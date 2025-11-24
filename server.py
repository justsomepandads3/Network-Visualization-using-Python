import socket

HOST = "0.0.0.0"
PORT = 5001
TOTAL_BYTES = 10_000

def recvall(conn, length):
    data = bytearray()
    while len(data) < length:
        chunk = conn.recv(length - len(data))
        if not chunk:
            raise ConnectionError("client disconnected early")
        data.extend(chunk)
    return bytes(data)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"Listening on {HOST}:{PORT} …")
    conn, addr = srv.accept()
    with conn:
        print(f"Client {addr} connected")
        payload = recvall(conn, TOTAL_BYTES)
        print(f"Received {len(payload)} bytes")
        conn.sendall(payload)  # echo back
        print("Echoed payload, closing connection")
