import os
import socket


# Server connection details
IP = "0.0.0.0"  # Change to server IPv4
PORT = 49152
ADDR = (IP, PORT)
SIZE = 1024  # Buffer size
FORMAT = "utf-8"
CLIENT_STORAGE = "client_storage"  # Local directory for client files

# Ensure the client storage directory exists
if not os.path.exists(CLIENT_STORAGE):
    os.makedirs(CLIENT_STORAGE)

def main():
    
    client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    client.connect(ADDR)
    print("[CONNECTED] Connected to the server.")

    # Authenticate with the server
    while True:  
        response = client.recv(SIZE).decode(FORMAT)
        cmd, msg = response.split("@", 1)
        print(msg)
        if cmd == "OK":
            if "authenticate" in msg.lower():
                username = input("Username: ")
                password = input("Password: ")
                client.send(f"{username}@{password}".encode(FORMAT))
            else:
                break
        elif cmd == "ERROR":
            print("[ERROR] Authentication failed. Try again.")
        
        data = input("> ").strip() 
        command = data.split(" ")
        
        cmd = command[0].upper()

        if cmd == "UPLOAD":
            if len(command) < 2:
                print("[ERROR] Specify the file path to upload.")
                continue

            filepath = command[1]
            if not os.path.exists(filepath):
                print("[ERROR] File does not exist.")
                continue

            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            client.send(f"{cmd}@{filename}@{filesize}".encode(FORMAT))

            with open(filepath, "rb") as f:
                chunk = f.read(SIZE)
                while chunk:
                    client.send(chunk)
                    chunk = f.read(SIZE)


            response = client.recv(SIZE).decode(FORMAT)
            cmd, msg = response.split("@", 1)
            print(msg)

        elif cmd == "DIR":
            client.send(cmd.encode(FORMAT))
            response = client.recv(SIZE).decode(FORMAT)
            cmd, msg = response.split("@", 1)
            if cmd == "OK":
                print("Files on server:")
                print(msg)
            else:
                print(f"[ERROR] {msg}")

        elif cmd == "LOGOUT":
            client.send(cmd.encode(FORMAT))
            print("[DISCONNECTED] Logged out from the server.")
            break

        else:
            print("[ERROR] Unknown command.")


    
    client.close() ## close the connection

if __name__ == "__main__":
    main()
