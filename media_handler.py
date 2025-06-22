import os
import io
import tempfile
import base64
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

try:
    import aiohttp
    import aiofiles
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    from nio.crypto.attachments import decrypt_attachment
    NIO_DECRYPT_AVAILABLE = True
except ImportError:
    NIO_DECRYPT_AVAILABLE = False

class MediaProcessor:
    """Class to handle Matrix media processing, download, upload, and encryption/decryption"""
    
    def __init__(self, temp_media_dir="./temp_media"):
        self.temp_media_dir = temp_media_dir
        
        # Ensure temp directory exists
        os.makedirs(self.temp_media_dir, exist_ok=True)
        print(f"✅ Temporary media directory ready: {self.temp_media_dir}")

    async def download_matrix_media(self, client, mxc_url, filename=None, encryption_info=None, original_mimetype=None):
        """Download and decrypt media from Matrix server with extensive debugging"""
        if not AIOHTTP_AVAILABLE:
            print("❌ Cannot download media - aiohttp not available")
            return None

        try:
            print(f"📥 Starting media download:")
            print(f"📥   MXC URL: {mxc_url}")
            print(f"📥   Filename: {filename}")
            print(f"📥   Original MIME Type: {original_mimetype}")
            print(f"📥   Has encryption info: {encryption_info is not None}")

            # Parse MXC URL (format: mxc://server/media_id)
            if not mxc_url.startswith("mxc://"):
                print(f"❌ Invalid MXC URL: {mxc_url}")
                return None

            # Download the media using matrix-nio's download method
            print(f"📥 Calling client.download()...")
            response = await client.download(mxc_url)

            print(f"📥 Download response type: {type(response)}")
            print(f"📥 Download response: {response}")

            if hasattr(response, 'body'):
                print(f"📥 ✅ Download successful - body size: {len(response.body)} bytes")

                # Check if we need to decrypt the content
                decrypted_data = response.body
                if encryption_info:
                    print(f"🔓 Attempting to decrypt media content...")
                    try:
                        # First try to decrypt using nio's crypto functions
                        if NIO_DECRYPT_AVAILABLE:
                            # Extract the actual base64 key string from the key dict
                            key_data = encryption_info.get('key', {})
                            if isinstance(key_data, dict):
                                key_b64 = key_data.get('k', '')
                                print(f"🔓 Extracted base64 key from dict: {key_b64[:10]}...")
                            else:
                                key_b64 = str(key_data)
                                print(f"🔓 Using key as string: {key_b64[:10]}...")

                            iv_b64 = encryption_info.get('iv', '')
                            hashes_data = encryption_info.get('hashes', {})
                            if isinstance(hashes_data, dict):
                                expected_hash = hashes_data.get('sha256', '')
                            else:
                                expected_hash = str(hashes_data)

                            print(f"🔓 Decryption parameters:")
                            print(f"🔓   Key (base64): {key_b64[:20]}...")
                            print(f"🔓   IV (base64): {iv_b64}")
                            print(f"🔓   Expected hash: {expected_hash[:20]}...")

                            # Use matrix-nio's decrypt_attachment with corrected parameters
                            decrypted_data = decrypt_attachment(
                                ciphertext=response.body,
                                key=key_b64,  # Pass the base64 string, not the dict
                                hash=expected_hash,
                                iv=iv_b64
                            )
                            print(f"🔓 ✅ Successfully decrypted media using nio - size: {len(decrypted_data)} bytes")
                        else:
                            raise ImportError("decrypt_attachment not available")

                    except ImportError:
                        print(f"⚠️ decrypt_attachment not available - trying alternative method")
                        if not CRYPTO_AVAILABLE:
                            print(f"❌ cryptography library not available - cannot decrypt")
                            print(f"💡 Install with: pip install cryptography")
                        else:
                            try:
                                # Alternative decryption method using base crypto
                                print(f"🔓 Using manual decryption...")

                                # Extract encryption parameters
                                key_data = encryption_info.get('key', {})
                                if isinstance(key_data, dict):
                                    key_b64 = key_data.get('k', '')
                                else:
                                    key_b64 = str(key_data)

                                iv_b64 = encryption_info.get('iv', '')
                                hashes_data = encryption_info.get('hashes', {})
                                if isinstance(hashes_data, dict):
                                    expected_hash = hashes_data.get('sha256', '')
                                else:
                                    expected_hash = str(hashes_data)

                                print(f"🔓   Key (first 20 chars): {key_b64[:20]}...")
                                print(f"🔓   IV: {iv_b64}")
                                print(f"🔓   Expected hash: {expected_hash[:16]}...")

                                # Decode base64 parameters
                                key = base64.b64decode(key_b64)
                                iv = base64.b64decode(iv_b64)

                                # Decrypt using AES-CTR
                                cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
                                decryptor = cipher.decryptor()
                                decrypted_data = decryptor.update(response.body) + decryptor.finalize()

                                # Verify hash if provided
                                if expected_hash:
                                    actual_hash = base64.b64encode(hashlib.sha256(decrypted_data).digest()).decode('utf-8')
                                    if actual_hash == expected_hash:
                                        print(f"🔓 ✅ Manual decryption successful and hash verified!")
                                    else:
                                        print(f"⚠️ Hash mismatch - decryption may have failed")
                                        print(f"     Expected: {expected_hash}")
                                        print(f"     Actual:   {actual_hash}")
                                else:
                                    print(f"🔓 ✅ Manual decryption completed (no hash to verify)")

                            except Exception as decrypt_error:
                                print(f"❌ Manual decryption failed: {decrypt_error}")
                                # Use original data if decryption fails
                                print(f"🔄 Using original encrypted data")
                                import traceback
                                traceback.print_exc()

                    except Exception as e:
                        print(f"❌ Decryption failed: {e}")
                        print(f"🔄 Using original encrypted data")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"📥 No encryption info provided - using downloaded data as-is")

                # Generate filename if not provided
                if not filename:
                    media_id = mxc_url.split('/')[-1]
                    # Use original MIME type to determine extension
                    if original_mimetype:
                        import mimetypes
                        ext = mimetypes.guess_extension(original_mimetype) or ""
                        filename = f"media_{media_id}{ext}"
                    else:
                        filename = f"media_{media_id}"

                # Save to temp directory
                filepath = Path(self.temp_media_dir) / filename

                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(decrypted_data)

                print(f"📥 ✅ Saved {'decrypted ' if encryption_info else ''}media to: {filepath}")
                print(f"📥 ✅ File size: {len(decrypted_data)} bytes")

                # Return both filepath and original MIME type for proper upload
                return str(filepath), original_mimetype
            else:
                print(f"❌ Download failed - no body in response: {response}")
                return None

        except Exception as e:
            print(f"❌ Error downloading media: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def upload_media_to_db(self, db_client, message_id, file_path, original_mimetype=None):
        """Upload media file to database API with debugging and MIME type preservation"""
        if not db_client:
            print(f"📤 Skipping media upload - DB client not available")
            return None

        try:
            print(f"📤 Uploading media to database:")
            print(f"📤   Message ID: {message_id}")
            print(f"📤   File path: {file_path}")
            print(f"📤   Original MIME type: {original_mimetype}")

            # Use the standard upload method from the simplified API client
            result = await db_client.upload_media(message_id, file_path)

            if result:
                print(f"📤 ✅ Uploaded media to database: {result}")

                # Clean up temp file
                try:
                    os.unlink(file_path)
                    print(f"🗑️ Cleaned up temp file: {file_path}")
                except:
                    pass

            return result
        except Exception as e:
            print(f"❌ Error uploading media to database: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def handle_encrypted_media_message(self, room, event, store_message_func=None, db_client=None, client=None):
        """Handle incoming ENCRYPTED media messages"""
        try:
            # Ignore own messages (handled by caller)
            
            # Determine media type
            media_type = "unknown"
            if hasattr(event, '__class__'):
                class_name = event.__class__.__name__
                if "Image" in class_name:
                    media_type = "image"
                elif "File" in class_name:
                    media_type = "file"
                elif "Audio" in class_name:
                    media_type = "audio"
                elif "Video" in class_name:
                    media_type = "video"

            print(f"📎🔐 ENCRYPTED MEDIA MESSAGE 🔒🎉")
            print(f"📎🔐   Room: {room.name}")
            print(f"📎🔐   From: {event.sender}")
            print(f"📎🔐   Type: {media_type}")
            print(f"📎🔐   Class: {type(event).__name__}")
            print(f"📎🔐   Decrypted: {event.decrypted}")
            print(f"📎🔐   Event ID: {event.event_id}")

            # Get media info with detailed logging
            media_url = getattr(event, 'url', None)
            filename = getattr(event, 'body', f"encrypted_media_{event.event_id}")
            mimetype = getattr(event, 'mimetype', None)

            print(f"📎🔐   Filename: {filename}")
            print(f"📎🔐   MXC URL: {media_url}")
            print(f"📎🔐   MIME Type: {mimetype}")

            # Extract encryption info properly
            encryption_info = None
            if hasattr(event, 'key') and hasattr(event, 'iv') and hasattr(event, 'hashes'):
                encryption_info = {
                    'key': event.key,  # This is already a dict with the 'k' field
                    'iv': event.iv,
                    'hashes': event.hashes
                }
                print(f"📎🔐   🔐 Extracted encryption info from event attributes")
                print(f"📎🔐   🔐 Key type: {type(event.key)}")
                print(f"📎🔐   🔐 Key preview: {str(event.key)[:50]}...")
            elif hasattr(event, 'file') and event.file:
                # Encryption info might be in the 'file' field
                file_info = event.file
                if isinstance(file_info, dict):
                    encryption_info = {
                        'key': file_info.get('key', {}),
                        'iv': file_info.get('iv'),
                        'hashes': file_info.get('hashes', {})
                    }
                    print(f"📎🔐   🔐 Extracted encryption info from file field")

            if encryption_info:
                print(f"📎🔐   🔐 Encryption info available: {encryption_info is not None}")
            else:
                print(f"📎🔐   ⚠️ No encryption info found!")

            # Store message in database first (without media file)
            stored_message = None
            if store_message_func:
                print(f"📁🔐 Storing encrypted media message in database...")
                stored_message = await store_message_func(
                    room_id=room.room_id,
                    event_id=event.event_id,
                    sender=event.sender,
                    message_type=media_type,
                    content=f"Encrypted media file: {filename}",
                    timestamp=datetime.fromtimestamp(event.server_timestamp / 1000)
                )

            # Download and upload media if we have database storage enabled
            if db_client and media_url and stored_message and client:
                print(f"📥🔐 Starting encrypted media download process...")

                # Download with original MIME type
                download_result = await self.download_matrix_media(
                    client,
                    media_url,
                    filename,
                    encryption_info,
                    original_mimetype=mimetype
                )

                if download_result:
                    if isinstance(download_result, tuple):
                        local_file_path, original_mimetype = download_result
                    else:
                        local_file_path = download_result
                        original_mimetype = mimetype

                    # Upload to database
                    message_id = stored_message.get('id')
                    if message_id:
                        print(f"📤🔐 Uploading decrypted media to database (message ID: {message_id})...")
                        await self.upload_media_to_db(db_client, message_id, local_file_path, original_mimetype)
                    else:
                        print("⚠️🔐 No message ID returned, cannot upload media")
                        # Clean up temp file
                        try:
                            os.unlink(local_file_path)
                        except:
                            pass
                else:
                    print("❌🔐 Failed to download encrypted media file")
            else:
                if not db_client:
                    print("⚠️🔐 Database not enabled, skipping encrypted media upload")
                elif not media_url:
                    print("⚠️🔐 No media URL found in encrypted event")
                elif not stored_message:
                    print("⚠️🔐 Failed to store encrypted message, skipping media upload")
                elif not client:
                    print("⚠️🔐 No Matrix client provided, cannot download media")

        except Exception as e:
            print(f"❌ Error in encrypted media message handling: {e}")
            import traceback
            traceback.print_exc()

    async def handle_media_message(self, room, event, store_message_func=None, db_client=None, client=None):
        """Handle incoming media messages with extensive debugging"""
        try:
            # Ignore own messages (handled by caller)
            
            # Determine media type
            media_type = "unknown"
            if hasattr(event, '__class__'):
                class_name = event.__class__.__name__
                if "Image" in class_name:
                    media_type = "image"
                elif "File" in class_name:
                    media_type = "file"
                elif "Audio" in class_name:
                    media_type = "audio"
                elif "Video" in class_name:
                    media_type = "video"

            print(f"📎 MEDIA MESSAGE 🎉")
            print(f"📎   Room: {room.name}")
            print(f"📎   From: {event.sender}")
            print(f"📎   Type: {media_type}")
            print(f"📎   Class: {type(event).__name__}")
            print(f"📎   Encrypted: {event.decrypted}")
            print(f"📎   Event ID: {event.event_id}")

            # Get media info with detailed logging
            media_url = getattr(event, 'url', None)
            filename = getattr(event, 'body', f"media_{event.event_id}")
            mimetype = getattr(event, 'mimetype', None)

            print(f"📎   Filename: {filename}")
            print(f"📎   MXC URL: {media_url}")
            print(f"📎   MIME Type: {mimetype}")

            # Check for encryption
            if hasattr(event, 'file'):
                print(f"📎   🔐 ENCRYPTED MEDIA DETECTED!")
                print(f"📎   File object: {event.file}")

            # Store message in database first (without media file)
            stored_message = None
            if store_message_func:
                print(f"📁 Storing media message in database...")
                stored_message = await store_message_func(
                    room_id=room.room_id,
                    event_id=event.event_id,
                    sender=event.sender,
                    message_type=media_type,
                    content=f"Media file: {filename}",
                    timestamp=datetime.fromtimestamp(event.server_timestamp / 1000)
                )

            # Download and upload media if we have database storage enabled
            if db_client and media_url and stored_message and client:
                print(f"📥 Starting media download process...")

                # Download the media file with original MIME type
                download_result = await self.download_matrix_media(
                    client,
                    media_url,
                    filename,
                    encryption_info=None,
                    original_mimetype=mimetype
                )

                if download_result:
                    if isinstance(download_result, tuple):
                        local_file_path, original_mimetype = download_result
                    else:
                        local_file_path = download_result
                        original_mimetype = mimetype

                    # Upload to database
                    message_id = stored_message.get('id')
                    if message_id:
                        print(f"📤 Uploading media to database (message ID: {message_id})...")
                        await self.upload_media_to_db(db_client, message_id, local_file_path, original_mimetype)
                    else:
                        print("⚠️ No message ID returned, cannot upload media")
                        # Clean up temp file
                        try:
                            os.unlink(local_file_path)
                        except:
                            pass
                else:
                    print("❌ Failed to download media file")
            else:
                if not db_client:
                    print("⚠️ Database not enabled, skipping media upload")
                elif not media_url:
                    print("⚠️ No media URL found in event")
                elif not stored_message:
                    print("⚠️ Failed to store message, skipping media upload")
                elif not client:
                    print("⚠️ No Matrix client provided, cannot download media")

        except Exception as e:
            print(f"❌ Error in media message handling: {e}")
            import traceback
            traceback.print_exc()

    async def send_file_attachment(self, client, room_id, file_path, description="File", store_message_func=None, db_client=None):
        """Send a file as an attachment to a room"""
        try:
            # Get file info first
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)

            # Determine mimetype
            if file_path.endswith('.txt'):
                mimetype = "text/plain"
            else:
                mimetype = "application/octet-stream"

            # Read the file and create a BytesIO object
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Wrap bytes in BytesIO to create a file-like object
            file_like_obj = io.BytesIO(file_data)

            # Upload the file to Matrix
            response, maybe_keys = await client.upload(
                file_like_obj,  # Pass file-like object instead of raw bytes
                content_type=mimetype,
                filename=filename,
                filesize=file_size
            )

            if hasattr(response, 'content_uri'):
                # Send the file message
                content = {
                    "body": filename,
                    "info": {
                        "size": file_size,
                        "mimetype": mimetype,
                    },
                    "msgtype": "m.file",
                    "url": response.content_uri,
                }

                # Add encryption info if file was encrypted
                if maybe_keys:
                    content["file"] = {
                        "url": response.content_uri,
                        "key": maybe_keys["key"],
                        "iv": maybe_keys["iv"],
                        "hashes": maybe_keys["hashes"],
                        "v": maybe_keys["v"]
                    }

                send_response = await client.room_send(
                    room_id=room_id,
                    message_type="m.room.message",
                    content=content,
                    ignore_unverified_devices=True
                )

                # Store file message in database
                if hasattr(send_response, 'event_id') and store_message_func:
                    db_result = await store_message_func(
                        room_id=room_id,
                        event_id=send_response.event_id,
                        sender=client.user_id,
                        message_type="file",
                        content=f"File: {filename} ({file_size} bytes)",
                        timestamp=datetime.now()
                    )

                    # Upload the actual file to database if message was stored
                    if db_result and 'id' in db_result and db_client:
                        try:
                            await db_client.upload_media(db_result['id'], file_path)
                            print(f"📁 Uploaded file to database: {filename}")
                        except Exception as upload_error:
                            print(f"⚠️ Failed to upload file to database: {upload_error}")

                print(f"File attachment sent: {filename} ({file_size} bytes)")
                return True
            else:
                print(f"File upload failed: {response}")
                return False

        except Exception as e:
            print(f"Error sending file attachment: {e}")
            import traceback
            traceback.print_exc()
            return False