import base64
import os
import queue
import socket
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class ProximityGUI:
    BASE_PORT = 5050
    MAX_PORT = 65535
    DISCONNECT_MESSAGE = "exit"

    def __init__(self, root):
        self.root = root
        self.root.title("Proximity")
        self.root.geometry("980x640")
        self.root.minsize(820, 540)

        self.mode = None
        self.username = ""
        self.server_name = ""
        self.ip = ""
        self.port = self.BASE_PORT
        self.passkey = ""

        self.server_socket = None
        self.client_socket = None
        self.clients = {}
        self.connected = False
        self.events = queue.Queue()

        self.colors = {
            "bg": "#f6f7f9",
            "panel": "#ffffff",
            "ink": "#17202a",
            "muted": "#657282",
            "line": "#d9dee7",
            "accent": "#1473e6",
            "accent_dark": "#0f5db8",
            "success": "#188a56",
            "danger": "#c24135",
        }

        self.root.configure(bg=self.colors["bg"])
        self.build_style()
        self.build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)
        self.root.after(100, self.process_events)

    def build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Panel.TFrame", background=self.colors["panel"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["ink"], font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=self.colors["panel"], foreground=self.colors["ink"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=self.colors["panel"], foreground=self.colors["ink"], font=("Segoe UI Semibold", 18))
        style.configure("Status.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))
        style.configure("Accent.TButton", background=self.colors["accent"], foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", self.colors["accent_dark"])])
        style.configure("Danger.TButton", background=self.colors["danger"], foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#9f332b")])
        style.configure("TEntry", fieldbackground="#ffffff", foreground=self.colors["ink"], padding=8)

    def build_layout(self):
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self.root, style="Panel.TFrame", padding=24)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)

        ttk.Label(sidebar, text="Proximity", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(sidebar, text="Offline chat rooms on your network", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 24))

        ttk.Label(sidebar, text="Host a room", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
        self.server_name_entry = ttk.Entry(sidebar, width=28)
        self.server_name_entry.grid(row=3, column=0, sticky="ew", pady=(8, 10))
        self.server_name_entry.insert(0, "Server")
        ttk.Button(sidebar, text="Start Server", style="Accent.TButton", command=self.start_server).grid(row=4, column=0, sticky="ew")

        ttk.Separator(sidebar).grid(row=5, column=0, sticky="ew", pady=22)

        ttk.Label(sidebar, text="Join a room", style="Panel.TLabel").grid(row=6, column=0, sticky="w")
        self.username_entry = ttk.Entry(sidebar, width=28)
        self.username_entry.grid(row=7, column=0, sticky="ew", pady=(8, 8))
        self.username_entry.insert(0, "Guest")
        self.passkey_entry = ttk.Entry(sidebar, width=28)
        self.passkey_entry.grid(row=8, column=0, sticky="new", pady=(0, 10))
        self.passkey_entry.insert(0, "Paste passkey")
        ttk.Button(sidebar, text="Join Chat", command=self.join_server).grid(row=9, column=0, sticky="ew")

        self.connection_card = ttk.Frame(sidebar, style="Panel.TFrame")
        self.connection_card.grid(row=10, column=0, sticky="ew", pady=(22, 0))
        ttk.Label(self.connection_card, text="Connection", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(self.connection_card, text="Not connected", style="Status.TLabel")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.passkey_label = ttk.Label(self.connection_card, text="", style="Muted.TLabel", wraplength=230)
        self.passkey_label.grid(row=2, column=0, sticky="w", pady=(8, 0))

        ttk.Button(sidebar, text="Disconnect", style="Danger.TButton", command=self.disconnect).grid(row=11, column=0, sticky="ew", pady=(24, 0))

        main = ttk.Frame(self.root, padding=24)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(header, text="Chat Room", font=("Segoe UI Semibold", 20), background=self.colors["bg"], foreground=self.colors["ink"]).grid(row=0, column=0, sticky="w")
        self.room_label = ttk.Label(header, text="Start or join a room to begin", foreground=self.colors["muted"])
        self.room_label.grid(row=1, column=0, sticky="w")

        chat_frame = ttk.Frame(main, style="Panel.TFrame", padding=14)
        chat_frame.grid(row=1, column=0, sticky="nsew")
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(0, weight=1)

        self.chat_log = tk.Text(
            chat_frame,
            wrap="word",
            state="disabled",
            bg="#ffffff",
            fg=self.colors["ink"],
            relief="flat",
            padx=10,
            pady=10,
            font=("Segoe UI", 10),
            spacing3=8,
        )
        self.chat_log.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(chat_frame, command=self.chat_log.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat_log.configure(yscrollcommand=scroll.set)

        composer = ttk.Frame(main)
        composer.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        composer.grid_columnconfigure(0, weight=1)
        self.message_entry = ttk.Entry(composer)
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.message_entry.bind("<Return>", lambda event: self.send_text())
        ttk.Button(composer, text="Attach File", command=self.send_file).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(composer, text="Attach Image", command=self.send_image).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(composer, text="Send", style="Accent.TButton", command=self.send_text).grid(row=0, column=3)

        self.write_log("Welcome to Proximity. Host a room or paste a passkey to join one.", "system")

    def get_local_ip(self):
        try:
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.connect(("8.8.8.8", 80))
            ip = temp_socket.getsockname()[0]
            temp_socket.close()
            return ip
        except OSError:
            return socket.gethostbyname(socket.gethostname())

    def make_passkey(self):
        return base64.b64encode("{}:{}".format(self.ip, self.port).encode("utf-8")).decode("utf-8")

    def decode_passkey(self, value):
        decoded = base64.b64decode(value.strip()).decode("utf-8")
        if ":" in decoded:
            ip, port = decoded.rsplit(":", 1)
            return ip, int(port)
        if len(decoded) == 8:
            return "192.168" + decoded.lstrip("0"), self.BASE_PORT
        if len(decoded) == 15:
            return decoded.lstrip("0"), self.BASE_PORT
        raise ValueError("Invalid passkey")

    def start_server(self):
        if self.connected:
            messagebox.showinfo("Already connected", "Disconnect before starting or joining another room.")
            return

        name = self.server_name_entry.get().strip()
        if not name.isalpha():
            messagebox.showerror("Invalid name", "Server name should only contain alphabets.")
            return

        self.mode = "server"
        self.server_name = name
        self.username = name
        self.ip = self.get_local_ip()
        self.port = self.BASE_PORT
        self.clients = {}

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.bind_server()
            self.server_socket.listen()
        except OSError as error:
            self.server_socket = None
            self.mode = None
            messagebox.showerror("Server error", str(error))
            return

        self.passkey = self.make_passkey()
        self.connected = True
        self.status_label.configure(text="Hosting on {}:{}".format(self.ip, self.port), foreground=self.colors["success"])
        self.passkey_label.configure(text="Passkey: {}".format(self.passkey))
        self.room_label.configure(text="Hosting as {}".format(self.server_name))
        self.write_log("Server started on {}:{}.".format(self.ip, self.port), "system")
        self.write_log("Share this passkey: {}".format(self.passkey), "system")

        threading.Thread(target=self.accept_connections, daemon=True).start()

    def bind_server(self):
        while self.port <= self.MAX_PORT:
            try:
                self.server_socket.bind((self.ip, self.port))
                return
            except OSError as error:
                if getattr(error, "winerror", None) == 10048 or getattr(error, "errno", None) == 98:
                    self.port += 1
                    continue
                raise
        raise OSError("No available port found.")

    def join_server(self):
        if self.connected:
            messagebox.showinfo("Already connected", "Disconnect before starting or joining another room.")
            return

        username = self.username_entry.get().strip()
        if not username.isalpha():
            messagebox.showerror("Invalid username", "Username should only contain alphabets.")
            return

        try:
            ip, port = self.decode_passkey(self.passkey_entry.get())
        except (ValueError, UnicodeDecodeError, base64.binascii.Error):
            messagebox.showerror("Invalid passkey", "Please enter a valid chat room passkey.")
            return

        self.mode = "client"
        self.username = username
        self.ip = ip
        self.port = port

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip, self.port))
        except OSError as error:
            self.client_socket = None
            self.mode = None
            messagebox.showerror("Connection failed", str(error))
            return

        self.connected = True
        self.status_label.configure(text="Connected to {}:{}".format(self.ip, self.port), foreground=self.colors["success"])
        self.passkey_label.configure(text="")
        self.room_label.configure(text="Joined as {}".format(self.username))
        self.write_log("Connected to {}:{}.".format(self.ip, self.port), "system")
        threading.Thread(target=self.receive_from_server, daemon=True).start()

    def accept_connections(self):
        while self.connected and self.server_socket:
            try:
                client, address = self.server_socket.accept()
                client.send("Connect".encode("utf-8"))
                client_name = client.recv(1024).decode("utf-8")
                final_name = client_name
                suffix = 1
                while final_name in self.clients.values():
                    final_name = "{}{}".format(client_name, suffix)
                    suffix += 1
                if client_name != final_name:
                    client.send(("\n \t Username updated to [" + final_name + "]").encode("utf-8"))
                self.clients[client] = final_name
                self.events.put(("system", "{} joined the room.".format(final_name)))
                self.broadcast("\n \t [{}] joined! \n".format(final_name).encode("utf-8"), client)
                client.send("Connected to [{}]!".format(self.server_name).encode("utf-8"))
                threading.Thread(target=self.receive_from_client, args=(client,), daemon=True).start()
            except OSError:
                break

    def receive_from_client(self, client):
        while self.connected:
            try:
                message = client.recv(1024).decode("utf-8")
                if not message:
                    break
                if message == self.DISCONNECT_MESSAGE:
                    break
                if message.startswith("image:"):
                    self.forward_file_payload(client, message, is_image=True)
                    continue
                if message.startswith("file:"):
                    self.forward_file_payload(client, message, is_image=False)
                    continue
                self.events.put(("message", message))
                self.broadcast(message.encode("utf-8"), client)
            except OSError:
                break
            except UnicodeDecodeError:
                continue

        user = self.clients.get(client, "A client")
        self.clients.pop(client, None)
        try:
            client.close()
        except OSError:
            pass
        self.events.put(("system", "{} disconnected.".format(user)))
        self.broadcast("\n \t [{}] left! \n".format(user).encode("utf-8"), client)

    def receive_from_server(self):
        while self.connected and self.client_socket:
            try:
                message = self.client_socket.recv(1024).decode("utf-8")
                if not message:
                    break
                if message == "Connect":
                    self.client_socket.send(self.username.encode("utf-8"))
                elif message == "Server left":
                    self.events.put(("system", "Server has disconnected."))
                    break
                elif message.startswith("image:"):
                    self.receive_file_payload(self.client_socket, message, is_image=True)
                elif message.startswith("file:"):
                    self.receive_file_payload(self.client_socket, message, is_image=False)
                elif "Username updated to [" in message:
                    self.username = message[25:-1]
                    self.events.put(("system", message.strip()))
                elif "Connected to" in message:
                    self.events.put(("system", message.strip()))
                else:
                    self.events.put(("message", message))
            except OSError:
                break
            except UnicodeDecodeError:
                continue
        self.events.put(("disconnect", "Disconnected."))

    def receive_file_payload(self, source_socket, header, is_image):
        try:
            if is_image:
                filename, size = header[7:].split()
                folder = "Proximity_images"
            else:
                filename, size = header[5:].split(";")
                folder = "Proximity_files"
            filename = os.path.basename(filename)
            size = int(size)
            os.makedirs(folder, exist_ok=True)
            output_path = os.path.join(folder, filename)
            remaining = size
            with open(output_path, "wb") as output_file:
                while remaining > 0:
                    chunk = source_socket.recv(min(512, remaining))
                    if not chunk:
                        break
                    output_file.write(chunk)
                    remaining -= len(chunk)
            self.events.put(("system", "Received {}: {}".format("image" if is_image else "file", output_path)))
        except (OSError, ValueError):
            self.events.put(("system", "Could not receive attachment."))

    def forward_file_payload(self, source_socket, header, is_image):
        try:
            if is_image:
                filename, size = header[7:].split()
                folder = "Proximity_images"
            else:
                filename, size = header[5:].split(";")
                folder = "Proximity_files"
            filename = os.path.basename(filename)
            size = int(size)
            os.makedirs(folder, exist_ok=True)
            output_path = os.path.join(folder, filename)
            targets = [client for client in list(self.clients.keys()) if client != source_socket]

            for target in targets:
                try:
                    target.send(header.encode("utf-8"))
                except OSError:
                    self.clients.pop(target, None)

            remaining = size
            with open(output_path, "wb") as output_file:
                while remaining > 0:
                    chunk = source_socket.recv(min(512, remaining))
                    if not chunk:
                        break
                    output_file.write(chunk)
                    remaining -= len(chunk)
                    for target in targets:
                        try:
                            target.sendall(chunk)
                        except OSError:
                            self.clients.pop(target, None)
            self.events.put(("system", "Received {}: {}".format("image" if is_image else "file", output_path)))
        except (OSError, ValueError):
            self.events.put(("system", "Could not receive attachment."))

    def send_text(self):
        text = self.message_entry.get().strip()
        if not text:
            return
        self.message_entry.delete(0, tk.END)
        if text == self.DISCONNECT_MESSAGE:
            self.disconnect()
            return
        if self.mode == "server":
            message = "[{}] : {}".format(self.server_name, text)
            self.broadcast(message.encode("utf-8"), "Server")
            self.write_log(message, "own")
        elif self.mode == "client" and self.client_socket:
            message = "[{}] : {}".format(self.username, text)
            try:
                self.client_socket.send(message.encode("utf-8"))
                self.write_log(message, "own")
            except OSError:
                self.write_log("Message could not be sent.", "system")
        else:
            messagebox.showinfo("Not connected", "Start or join a room before sending messages.")

    def send_file(self):
        path = filedialog.askopenfilename(title="Choose a file")
        if path:
            self.send_attachment(path, is_image=False)

    def send_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )
        if path:
            self.send_attachment(path, is_image=True)

    def send_attachment(self, path, is_image):
        if not self.connected:
            messagebox.showinfo("Not connected", "Start or join a room before sending attachments.")
            return
        try:
            size = os.path.getsize(path)
            name = os.path.basename(path)
            if is_image:
                header = "image: {} {}".format(name, size)
            else:
                header = "file:{};{}".format(path, size)
            if self.mode == "server":
                self.broadcast(header.encode("utf-8"), "Server")
                self.broadcast_file_bytes(path, "Server")
            else:
                self.client_socket.send(header.encode("utf-8"))
                self.send_file_bytes(self.client_socket, path)
            self.write_log("Sent {}: {}".format("image" if is_image else "file", name), "own")
        except OSError as error:
            messagebox.showerror("Attachment failed", str(error))

    def send_file_bytes(self, target_socket, path):
        with open(path, "rb") as input_file:
            while True:
                chunk = input_file.read(512)
                if not chunk:
                    break
                target_socket.sendall(chunk)

    def broadcast_file_bytes(self, path, current_client):
        for client in list(self.clients.keys()):
            if client == current_client:
                continue
            try:
                self.send_file_bytes(client, path)
            except OSError:
                self.clients.pop(client, None)

    def broadcast(self, message, current_client):
        for client in list(self.clients.keys()):
            if client == current_client:
                continue
            try:
                client.send(message)
            except OSError:
                self.clients.pop(client, None)

    def process_events(self):
        while True:
            try:
                event_type, message = self.events.get_nowait()
            except queue.Empty:
                break
            if event_type == "disconnect":
                self.write_log(message, "system")
                self.disconnect(update_log=False)
            else:
                self.write_log(message, event_type)
        self.root.after(100, self.process_events)

    def write_log(self, message, tag):
        self.chat_log.configure(state="normal")
        self.chat_log.tag_configure("system", foreground=self.colors["muted"])
        self.chat_log.tag_configure("message", foreground=self.colors["ink"])
        self.chat_log.tag_configure("own", foreground=self.colors["accent"])
        self.chat_log.insert(tk.END, message.strip() + "\n", tag)
        self.chat_log.configure(state="disabled")
        self.chat_log.see(tk.END)

    def disconnect(self, update_log=True):
        if self.mode == "server":
            self.broadcast("Server left".encode("utf-8"), "Server")
        elif self.mode == "client" and self.client_socket:
            try:
                self.client_socket.send(self.DISCONNECT_MESSAGE.encode("utf-8"))
            except OSError:
                pass

        self.connected = False
        for client in list(self.clients.keys()):
            try:
                client.close()
            except OSError:
                pass
        self.clients = {}

        for sock in (self.client_socket, self.server_socket):
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
        self.client_socket = None
        self.server_socket = None
        self.mode = None

        self.status_label.configure(text="Not connected", foreground=self.colors["muted"])
        self.passkey_label.configure(text="")
        self.room_label.configure(text="Start or join a room to begin")
        if update_log:
            self.write_log("Disconnected.", "system")

    def close_app(self):
        self.disconnect(update_log=False)
        self.root.destroy()


if __name__ == "__main__":
    app_root = tk.Tk()
    ProximityGUI(app_root)
    app_root.mainloop()
