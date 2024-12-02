import os
import socket
import time
from cryptography.fernet import Fernet
from client_network_analysis import NetworkStats


# Server connection details
IP = "192.168.1.12"  # Change to server IPv4
PORT = 49157
ADDR = (IP, PORT)
SIZE = 1024  # Buffer size
FORMAT = "utf-8"
CLIENT_STORAGE = "client_storage"  # Local directory for client files
stats_logger = NetworkStats()



# Ensure the client storage directory exists
if not os.path.exists(CLIENT_STORAGE):
    os.makedirs(CLIENT_STORAGE)

def load_key():
    # Load the key from the file
    with open("key.key", "rb") as key_file:
        return key_file.read()

def authenticate(client, username, password):
    key = load_key()
    fernet = Fernet(key)

    # Encrypt the password
    encrypted_password = fernet.encrypt(password.encode())

    # Send the username and encrypted password to the server
    client.send(f"AUTH@{username}@{encrypted_password.decode()}".encode(FORMAT))
    response = client.recv(SIZE).decode(FORMAT)
    cmd, msg = response.split("@", 1)
    if cmd == "OK":
        print(f"[SUCCESS] {msg}")
        return True
    else:
        print(f"[ERROR] {msg}")
        return False



def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    print("[CONNECTED] Connected to the server.")
    
    response = client.recv(SIZE).decode(FORMAT)
    print(response)
    # Authentication loop
    while True:
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()

        if authenticate(client, username, password):
            break
        else:
            print("[ERROR] Authentication failed. Try again.")

    # Command loop
    while True:        
        # Input 
        data = input("> ").strip()
        command = data.split(" ")
        cmd = command[0].upper()

        if cmd == "LOGOUT":
            start_time = time.perf_counter()  # Start timing for LOGOUT
            client.send(cmd.encode(FORMAT))
            response = client.recv(SIZE).decode(FORMAT)  # To ensure response time is logged
            end_time = time.perf_counter()  # End timing
            stats_logger.record_response_time(cmd, start_time, end_time)  # Log response time
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
            if response.startswith("ERROR@File"):
                # Server asks if we want to overwrite
                print(response.split("@", 1)[1])
                overwrite = input("Do you want to overwrite? (yes/no): ").strip().lower()

                # Send overwrite decision to server
                client.send(overwrite.encode(FORMAT))
                response = client.recv(SIZE).decode(FORMAT)

                # Handle response to overwrite decision
                if response.startswith("ERROR@"):
                    print(response.split("@", 1)[1])
                    continue  # Ensure client returns to main loop for new commands

            elif response.startswith("ERROR@"):
                print(response.split("@", 1)[1])
                continue

            startU = time.perf_counter()  # Start timing upload
            # Proceed to upload the file
            with open(filepath, "rb") as f:
                chunk = f.read(SIZE)
                while chunk:
                    client.send(chunk)
                    chunk = f.read(SIZE)

            endU = time.perf_counter()  # End timing upload
            stats_logger.record_response_time(cmd, startU, endU, filename=filename, filesize=filesize)  # Log upload stats

            # Wait for server confirmation
            response = client.recv(SIZE).decode(FORMAT)
            cmd, msg = response.split("@", 1)
            if cmd == "OK":
                print(f"[SUCCESS] {msg}")
            elif cmd == "ERROR":
                print(f"[ERROR] {msg}")

        elif cmd == "DIR":
            start_time = time.perf_counter()  # Start timing for DIR
            # Send the command to the server
            client.send(cmd.encode(FORMAT))

            # Receive and process the server's response
            response = client.recv(SIZE).decode(FORMAT)
            end_time = time.perf_counter()  # End timing
            stats_logger.record_response_time(cmd, start_time, end_time)  # Log response time

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
                _, server_filename, filesize = response.split("@")
                filesize = int(filesize)  # Convert to an integer
                print(f"Downloading file: {server_filename} ({filesize} bytes)")

                # Open a file to write the incoming data
                filepath = os.path.join(CLIENT_STORAGE, filename)

                startD = time.perf_counter()  # Start timing download
                with open(filepath, "wb") as f:
                    bytes_received = 0
                    while bytes_received < filesize:
                        chunk = client.recv(min(SIZE, filesize - bytes_received))
                        f.write(chunk)
                        bytes_received += len(chunk)
                endD = time.perf_counter()  # End timing download
                stats_logger.record_response_time(cmd, startD, endD, filename=server_filename, filesize=filesize)  # Log download stats
                
                print(f"[DOWNLOAD COMPLETE] File {filename} downloaded successfully.")
                

        elif cmd == "CREATE":
            # Check if the subfolder name is provided
            if len(command) < 2:
                print("[ERROR] Specify the subfolder name to create.")
                continue

            subfolder_name = command[1].strip()
            print(f"[DEBUG] Sending CREATE command: {cmd}@{subfolder_name}")  # Debug log
            
            # Send CREATE request to the server
            client.send(f"{cmd}@{subfolder_name}".encode(FORMAT))

             # Receive and interpret the server's response
            response = client.recv(SIZE).decode(FORMAT)
            cmd, msg = response.split("@", 1)
            print(f"Sent CREATE command: {cmd}@{subfolder_name}")


        elif cmd == "DELETE":
            # Check for filename argument
            if len(command) < 2:
                print("[ERROR] Specify the file name to delete.")
                continue

            filename = command[1].strip()
            start_time = time.perf_counter()  # Start timing delete
            # Send DELETE request to the server
            client.send(f"{cmd}@{filename}".encode(FORMAT))

            # Receive and interpret server's response
            response = client.recv(SIZE).decode(FORMAT)
            end_time = time.perf_counter()  # End timing delete
            stats_logger.record_response_time(cmd, start_time, end_time)  # Log response time


            cmd, msg = response.split("@", 1)

            if cmd == "OK":
                print(f"[SUCCESS] {msg}")
            elif cmd == "ERROR":
                print(f"[ERROR] {msg}")
            else:
                print("[ERROR] Unexpected response from the server.")
    
    stats_logger.save_stats_to_csv("client_network_stats.csv")
    client.close()  # Close the connection



if __name__ == "__main__":
    main()

