import os
import socket
import threading
import hashlib

IP = "0.0.0.0" # Change to server IPv4
PORT = 49152
ADDR = (IP,PORT)
SIZE = 1024
FORMAT = "utf-8"
SERVER_PATH = "server_storage"  # Directory to store files

# Simulated user database with hashed passwords
USERS = {
    "user1": hashlib.sha256("password1".encode(FORMAT)).hexdigest(),
    "user2": hashlib.sha256("password2".encode(FORMAT)).hexdigest()
}

def authenticate(username, password):
    # Authenticate user using hashed passwords
    hashed_input = hashlib.sha256(password.encode(FORMAT)).hexdigest()
    return USERS.get(username) == hashed_input

# Ensure the server storage directory exists
if not os.path.exists(SERVER_PATH):
    os.makedirs(SERVER_PATH)

def handle_client (conn,addr):


    print(f"[NEW CONNECTION] {addr} connected.")
    conn.send("OK@Welcome to the server. Please authenticate.".encode(FORMAT))

    authenticated = False
    while not authenticated:
        credentials = conn.recv(SIZE).decode(FORMAT).split("@")
        if len(credentials) < 2:
            conn.send("ERROR@Invalid credentials format.".encode(FORMAT))
            continue
        username, password = credentials
        if authenticate(username, password):
            authenticated = True
            conn.send("OK@Authentication successful.".encode(FORMAT))
        else:
            conn.send("ERROR@Invalid username or password.".encode(FORMAT))
    
    while True:
        try:
            data =  conn.recv(SIZE).decode(FORMAT)
            data = data.split("@")
            cmd = data[0]
           
            send_data = "OK@"

            if cmd == "LOGOUT":
                break

            elif cmd == "UPLOAD":
                filename = data[1]
                filesize = int(data[2])
                filepath = os.path.join(SERVER_PATH, filename)
                with open(filepath, "wb") as f:
                    remaining = filesize
                    while remaining > 0:
                        chunk = conn.recv(min(SIZE, remaining))
                        f.write(chunk)
                        remaining -= len(chunk)
                conn.send("OK@File uploaded successfully.".encode(FORMAT))
            elif cmd == "DIR":
                files = os.listdir(SERVER_PATH)
                file_list = "\n".join(files)
                conn.send(f"OK@{file_list}".encode(FORMAT))

            elif cmd == "DOWNLOAD":
                filename = data[1]
                filepath = os.path.join(SERVER_PATH, filename)
                ## if file is not found
                if not os.path.isfile(filepath):
                    conn.send("[ERROR] File not found".encode(FORMAT))
                else:
                    with open(filename, "rb") as f:
                        ## read the file in chunks and send
                        while(chunk:= f.read(SIZE)):
                            conn.send(chunk)
                    conn.send(f"OK@Ready to send {filename}".encode(FORMAT))


            else:
                conn.send("ERROR@Invalid command.".encode(FORMAT))
                
        except Exception as e:
            print(f"[ERROR] {e}")
            conn.send("ERROR@An error occurred.".encode(FORMAT))
            break


    print(f"[DISCONNECTED] {addr} disconnected")
    conn.close()


def main():
    print("Starting the server")
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM) ## used IPV4 and TCP connection
    server.bind(ADDR) # bind the address
    server.listen() ## start listening
    print(f"server is listening on {IP}: {PORT}")
    while True:
        conn, addr = server.accept() ### accept a connection from a client
        thread = threading.Thread(target = handle_client, args = (conn, addr)) ## assigning a thread for each client
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


if __name__ == "__main__":
    main()
