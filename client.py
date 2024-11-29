import os
import socket


# Server connection details
IP = "192.168.4.146"  # Change to server IPv4
PORT = 49157
ADDR = (IP, PORT)
SIZE = 1024  # Buffer size
FORMAT = "utf-8"
CLIENT_STORAGE = "client_storage"  # Local directory for client files

# Ensure the client storage directory exists
if not os.path.exists(CLIENT_STORAGE):
    os.makedirs(CLIENT_STORAGE)

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    print("[CONNECTED] Connected to the server.")
    response = client.recv(SIZE).decode(FORMAT)
    print(response)

    while True:        

        # Input command from the client
        data = input("> ").strip()
        command = data.split(" ")
        cmd = command[0].upper()

        if cmd == "LOGOUT":
            client.send(cmd.encode(FORMAT))
            print("[DISCONNECTED] Logged out from the server.")
            break
        elif cmd == "UPLOAD":
            if len(command) < 2:
                print("[ERROR] Specify the file path to upload.")
                continue

            filepath = command[1]
            if not os.path.exists(filepath):
                print("[ERROR] File does not exist.")
                continue

            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)

            print(f"Uploading file: {filename}, Size: {filesize} bytes")

            # Send the command to the server with file details
            client.send(f"{cmd}@{filename}@{filesize}".encode(FORMAT))

            # Wait for server response
            response = client.recv(SIZE).decode(FORMAT)
            if response.startswith("ERROR@File already exists"):
                print(response.split("@", 1)[1])
                overwrite = input("Overwrite the file? (yes/no): ").strip().lower()
                client.send(overwrite.encode(FORMAT))
                if overwrite != "yes":
                    print("[UPLOAD CANCELLED] The file was not uploaded.")
                    continue

            # Send the file content in chunks
            with open(filepath, "rb") as f:
                chunk = f.read(SIZE)
                while chunk:
                    client.send(chunk)
                    chunk = f.read(SIZE)

            # Send a special message to indicate the end of file transfer
            client.send(b'END_FILE')

            # Wait for server confirmation
            response = client.recv(SIZE).decode(FORMAT)
            cmd, msg = response.split("@", 1)
            print(msg)

        elif cmd == "DIR":
            # Send the command to the server
            client.send(cmd.encode(FORMAT))

            # Receive and process the server's response
            response = client.recv(SIZE).decode(FORMAT)
            cmd, msg = response.split("@", 1)
            if cmd == "OK":
                print("Files on server:")
                print(msg)
            else:
                print(f"[ERROR] {msg}")
                
        elif cmd == "DOWNLOAD":
            if len(command) < 2:
                print("[ERROR] Specify the file name to download.")
                continue

            filename = command[1]

            # Send the DOWNLOAD command to the server
            client.send(f"{cmd}@{filename}".encode(FORMAT))

            # Wait for the server response
            response = client.recv(SIZE).decode(FORMAT)
            if response.startswith("ERROR"):
                print(response.split("@", 1)[1])
                continue

            if response.startswith("OK"):
                print(f"Downloading file: {filename}")

                # Open a file to write the incoming data
                filepath = os.path.join(CLIENT_STORAGE, filename)
                with open(filepath, "wb") as f:
                    while True:
                        chunk = client.recv(SIZE)
                        if chunk == b"END_FILE":
                            print(f"[DOWNLOAD COMPLETE] File {filename} downloaded successfully.")
                            break
                        f.write(chunk)

                # Control returns here after the download loop ends


        elif cmd == "DELETE":
            # Check for filename argument
            if len(command) < 2:
                print("[ERROR] Specify the file name to delete.")
                continue

            filename = command[1].strip()

            # Send DELETE request to the server
            client.send(f"{cmd}@{filename}".encode(FORMAT))

            # Receive and interpret server's response
            response = client.recv(SIZE).decode(FORMAT)
            cmd, msg = response.split("@", 1)

            if cmd == "OK":
                print(f"[SUCCESS] {msg}")
            elif cmd == "ERROR":
                print(f"[ERROR] {msg}")
            else:
                print("[ERROR] Unexpected response from the server.")

    client.close()  # Close the connection



if __name__ == "__main__":
    main()

