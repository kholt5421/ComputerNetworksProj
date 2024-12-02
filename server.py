import os
import socket
import threading
import time  # To measure response time
import hashlib
import signal

from cryptography.fernet import Fernet
from network_stats import NetworkStats

IP = "10.200.232.146" # Change to server IPv4
PORT = 49157
ADDR = (IP,PORT)
SIZE = 1024
FORMAT = "utf-8"
SERVER_PATH = "server_storage"  # Directory to store files
stats_logger = NetworkStats()
is_running = True

# Set up a signal handler to capture keyboard interrupt in order to close the server
def signal_handler(sig, frame):
    global is_running
    print("\n[INFO] Interrupt received. Shutting down server...")
    is_running = False

signal.signal(signal.SIGINT, signal_handler)

# Ensure the server storage directory exists
if not os.path.exists(SERVER_PATH):
    os.makedirs(SERVER_PATH)

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# Example: Generate hashed passwords for users
USERS = {
    "user1": hash_password("password1"),
    "user2": hash_password("password2")
}

def load_key():
    # Load the key from the file
    with open("key.key", "rb") as key_file:
        return key_file.read()

# Load the key
key = load_key()
fernet = Fernet(key)

# Authenticate user using encrypted password
def authenticate(username, encrypted_password):
    try:
        # Decrypt the password
        decrypted_password = fernet.decrypt(encrypted_password.encode()).decode()

        # Hash the decrypted password and check against stored hash
        hashed_input = hashlib.sha256(decrypted_password.encode(FORMAT)).hexdigest()
        return USERS.get(username) == hashed_input
    except Exception as e:
        print(f"[ERROR] Decryption failed: {e}")
        return False


def handle_client(conn, addr):
    authenticated = False
    username = None  # Store the authenticated username
    print(f"\n[NEW CONNECTION] {addr} connected.")
    conn.send("Welcome to the server".encode(FORMAT))

    while True:
        try:
            # Receive a command from the client
            data = conn.recv(SIZE).decode(FORMAT)
            if not data:
                print(f"[DISCONNECTED] {addr} disconnected.")
                break

            #print(f"[RECEIVED DATA] {data} from {addr}")
            command = data.split("@")
            cmd = command[0]
            if not authenticated:
                if cmd == "AUTH":
                    username = command[1]
                    encrypted_password = command[2]
                    if authenticate(username, encrypted_password):
                        authenticated = True
                        conn.send("OK@Authentication successful.".encode(FORMAT))
                    else:
                        conn.send("ERROR@Invalid credentials.".encode(FORMAT))
                else:
                    conn.send("ERROR@Please authenticate first.".encode(FORMAT))
                continue
            
            if cmd == "LOGOUT":
                # Log the user out
                start_time = time.perf_counter()
                conn.send("OK@Logged out".encode(FORMAT))
                stats_logger.record_response_time(cmd, start_time, end_time)    
                print(f"[DISCONNECTED] {addr} logged out.")
                break

            elif cmd == "UPLOAD":
                filename = command[1]
                filesize = int(command[2])
                filepath = os.path.join(SERVER_PATH, filename)

                # Check if the file exists
                if os.path.exists(filepath):
                    # Notify the client about the existing file
                    conn.send(f"ERROR@File {filename} already exists.".encode(FORMAT))
                    
                    # Wait for client response
                    overwrite = conn.recv(SIZE).decode(FORMAT).strip().lower()
                    if overwrite != "yes":
                        conn.send("ERROR@Upload cancelled by user.".encode(FORMAT))
                        print(f"[UPLOAD CANCELLED] Client declined to overwrite {filename}.")
                        continue  # Ensure proper exit to process further commands

                # Notify the client that the server is ready to receive the file
                conn.send("OK@Ready to receive file".encode(FORMAT))

                start_time = time.perf_counter()
                
                # Open the file to write incoming data
                with open(filepath, "wb") as f:
                    bytes_received = 0
                    while bytes_received < filesize:
                        chunk = conn.recv(SIZE)
                        f.write(chunk)
                        bytes_received += len(chunk)

                end_time = time.perf_counter()
                stats_logger.record_upload(filename, filesize, start_time, end_time)
                
                print(f"[UPLOAD COMPLETE] File {filename} uploaded successfully.")
                conn.send(f"OK@File {filename} uploaded successfully.".encode(FORMAT))

            elif cmd == "DIR":
                start_time = time.perf_counter()
                
                # Handle directory listing
                try:
                    files = os.listdir(SERVER_PATH)
                    if files:
                        file_list = "\n".join(files)
                    else:
                        file_list = "No files in the server directory."
                    conn.send(f"OK@{file_list}".encode(FORMAT))

                    
                except Exception as e:
                    print(f"[ERROR] Failed to list directory contents: {e}")
                    conn.send(f"ERROR@Failed to list directory contents.".encode(FORMAT))
                finally:
                    end_time = time.perf_counter()  # End timing
                    stats_logger.record_response_time(cmd, start_time, end_time)    

            elif cmd == "DOWNLOAD":
                filename = command[1]
                filepath = os.path.join(SERVER_PATH, filename)

                # Check if the file exists
                if not os.path.isfile(filepath):
                    conn.send(f"ERROR@File {filename} not found.".encode(FORMAT))
                else:
                    filesize = os.path.getsize(filepath)
                    conn.send(f"OK@{filename}@{filesize}".encode(FORMAT))  # Send metadata

                    start_time = time.perf_counter()
                    # Open the file and send its content in chunks
                    with open(filepath, "rb") as f:
                        while (chunk := f.read(SIZE)):
                            conn.send(chunk)

                    # Send end-of-file marker
                    conn.send(b"END_FILE")

                    end_time = time.perf_counter()
                    stats_logger.record_download(filename, filesize, start_time, end_time)
                    
                    print(f"[DOWNLOAD COMPLETE] File {filename} sent to {addr}.")
            
            elif cmd == "CREATE":
                start_time = time.perf_counter()
                subfolder_path = os.path.join(SERVER_PATH, command[1])
                try:
                    os.makedirs(subfolder_path, exist_ok=True)
                    conn.send(f"OK@Subfolder '{command[1]}' created successfully.".encode(FORMAT))
                except Exception as e:
                    conn.send(f"ERROR@Failed to create subfolder: {e}".encode(FORMAT))
                    print(f"Received command: {cmd} with argument {command[1]}")

                finally:
                    end_time = time.perf_counter()  # End timing
                    stats_logger.record_response_time(cmd, start_time, end_time)

            elif cmd == "DELETE":
                start_time = time.perf_counter()
                
                name = command[1]
                path = os.path.join(SERVER_PATH, name)

                # Check if the file exists
                if not os.path.isfile(path) and not os.path.isdir(path):
                    send_data = f"ERROR@File '{name}' not found."
                elif os.path.isfile(path):
                    try:
                        # Attempt to delete the file
                        os.remove(path)                       
                        send_data = f"OK@File '{name}' deleted successfully."

                    except Exception as e:
                        conn.send(f"ERROR@Failed to delete subfolder: {e}".encode(FORMAT))

                elif os.path.isdir(path):
                    try:
                        # Attempt to delete the subfolder
                        os.rmdir(path)                        
                        send_data = f"OK@Subdirectory '{name}' deleted successfully."

                    except Exception as e:
                        send_data = f"ERROR@Failed to delete subdirectory '{name}': {e}"
                # Send the response to the client
                conn.send(send_data.encode(FORMAT))

                end_time = time.perf_counter()  # End tracking the command execution time
                stats_logger.record_response_time(cmd, start_time, end_time)  # Log the response time

            else:
                # Unknown command
                conn.send("ERROR@Invalid command.".encode(FORMAT))
                print(f"[ERROR] Unknown command received: {cmd}")

        except Exception as e:
                # Handle general exceptions for the entire loop
                print(f"[ERROR] Exception with client {addr}: {e}")
                conn.send(f"ERROR@Unexpected error: {e}".encode(FORMAT))
                break  # Exit the loop on critical error

    conn.close()
    print(f"[CONNECTION CLOSED] {addr}")
               

def main():
    global is_running
    # Main server function to accept and manage connections.
    print("[STARTING] Server is starting...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    print(f"[LISTENING] Server is listening on {IP}:{PORT}")

    try:
        while is_running:
            server.settimeout(0.1)  # Allow periodic checks
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.start()
                print(f"\n[ACTIVE CONNECTIONS] {threading.active_count() - 2}")
            except socket.timeout:
                continue

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        server.close()
        stats_logger.save_stats_to_csv("server_network_stats.csv")
        print("[INFO] Server network statistics saved.")
        print("[SHUTDOWN] Server has shut down.")
        
if __name__ == "__main__":
    main()

