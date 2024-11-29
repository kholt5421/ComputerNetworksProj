import os
import socket
import threading
import hashlib
import time  # To measure response time

IP = "192.168.4.146" # Change to server IPv4
PORT = 49157
ADDR = (IP,PORT)
SIZE = 1024
FORMAT = "utf-8"
SERVER_PATH = "server_storage"  # Directory to store files

# Ensure the server storage directory exists
if not os.path.exists(SERVER_PATH):
    os.makedirs(SERVER_PATH)
    
def handle_client(conn, addr):
   
    print(f"[NEW CONNECTION] {addr} connected.")
    conn.send("Welcome to the server".encode(FORMAT))

    while True:
        try:
            # Receive a command from the client
            data = conn.recv(SIZE).decode(FORMAT)
            if not data:
                print(f"[DISCONNECTED] {addr} disconnected.")
                break

            print(f"[RECEIVED DATA] {data} from {addr}")
            command = data.split("@")
            cmd = command[0]

            if cmd == "LOGOUT":
                # Log the user out
                conn.send("OK@Logged out".encode(FORMAT))
                print(f"[DISCONNECTED] {addr} logged out.")
                break

            elif cmd == "UPLOAD":
                # Handle file upload
                filename = command[1]
                filesize = int(command[2])
                filepath = os.path.join(SERVER_PATH, filename)

                # Check for existing file
                if os.path.exists(filepath):
                    conn.send(f"ERROR@File {filename} already exists.".encode(FORMAT))
                    overwrite = conn.recv(SIZE).decode(FORMAT).strip().lower()
                    if overwrite != "yes":
                        conn.send("ERROR@Upload cancelled.".encode(FORMAT))
                        continue

                conn.send("OK@Ready to receive file".encode(FORMAT))

                # Receive the file data in chunks
                with open(filepath, "wb") as f:
                    bytes_received = 0
                    while bytes_received < filesize:
                        chunk = conn.recv(SIZE)
                        if chunk == b"END_FILE":
                            break
                        f.write(chunk)
                        bytes_received += len(chunk)

                print(f"[UPLOAD COMPLETE] File {filename} uploaded by {addr}.")
                conn.send(f"OK@File {filename} uploaded successfully.".encode(FORMAT))

            elif cmd == "DIR":
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
                    
            elif cmd == "DOWNLOAD":
                filename = command[1]
                filepath = os.path.join(SERVER_PATH, filename)

                # Check if the file exists
                if not os.path.isfile(filepath):
                    conn.send(f"ERROR@File {filename} not found.".encode(FORMAT))
                else:
                    conn.send(f"OK@Ready to send {filename}".encode(FORMAT))

                    # Open the file and send its content in chunks
                    with open(filepath, "rb") as f:
                        while (chunk := f.read(SIZE)):
                            conn.send(chunk)

                    # Send end-of-file marker
                    conn.send(b"END_FILE")
                    print(f"[DOWNLOAD COMPLETE] File {filename} sent to {addr}.")
            
            elif cmd == "DELETE":
                # Parse the filename from the client command
                filename = command[1]
                filepath = os.path.join(SERVER_PATH, filename)

                # Check if the file exists
                if not os.path.isfile(filepath):
                    send_data = f"ERROR@File '{filename}' not found."
                else:
                    try:
                        # Attempt to delete the file
                        os.remove(filepath)
                        send_data = f"OK@File '{filename}' deleted successfully."
                    except Exception as e:
                        send_data = f"ERROR@Failed to delete file '{filename}': {e}"

                # Send the response to the client
                conn.send(send_data.encode(FORMAT))


            else:
                # Unknown command
                conn.send("ERROR@Invalid command.".encode(FORMAT))
                print(f"[ERROR] Unknown command received: {cmd}")

            

        except Exception as e:
            print(f"[ERROR] Exception with client {addr}: {e}")
            break

    conn.close()
    print(f"[CONNECTION CLOSED] {addr}")


def main():
    # Main server function to accept and manage connections.
    print("[STARTING] Server is starting...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    print(f"[LISTENING] Server is listening on {IP}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"\n[ACTIVE CONNECTIONS] {threading.active_count() - 2}")


if __name__ == "__main__":
    main()
