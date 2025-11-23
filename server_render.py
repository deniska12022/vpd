import socket
import cv2
import numpy as np
import struct
import threading
import os
import time
from flask import Flask, render_template
from threading import Thread

# Создаем Flask app для здоровья сервиса
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Video Hub Server is running!"

@app.route('/health')
def health():
    return "OK"

class RenderVideoHub:
    def __init__(self):
        self.host = '0.0.0.0'
        self.port = int(os.environ.get('PORT', 10000))
        self.socket_server = None
        self.clients = {}
        self.controllers = {}
        self.running = True
        
    def start_socket_server(self):
        """Запуск TCP-сокет сервера"""
        try:
            self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_server.bind((self.host, self.port))
            self.socket_server.listen(10)
            
            print(f"🚀 Video Hub запущен на {self.host}:{self.port}")
            print("📡 Ожидаем подключения камер и контроллеров...")
            
            while self.running:
                conn, addr = self.socket_server.accept()
                print(f"🔗 Новое подключение от: {addr}")
                
                # Определяем тип клиента
                client_thread = Thread(target=self.handle_client, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()
                
        except Exception as e:
            print(f"❌ Ошибка сокет-сервера: {e}")
        finally:
            if self.socket_server:
                self.socket_server.close()
    
    def handle_client(self, conn, addr):
        """Обработка клиентского подключения"""
        try:
            # Получаем тип клиента (первые 10 байт)
            client_type_data = conn.recv(10)
            if not client_type_data:
                return
                
            client_type = client_type_data.decode('utf-8').strip()
            client_id = f"{addr[0]}:{addr[1]}"
            
            if client_type == "CAMERA":
                print(f"📹 Подключена камера: {client_id}")
                self.handle_camera(conn, client_id)
            elif client_type == "CONTROLLER":
                print(f"🎮 Подключен контроллер: {client_id}")
                self.handle_controller(conn, client_id)
            else:
                conn.close()
                
        except Exception as e:
            print(f"❌ Ошибка обработки клиента: {e}")
            conn.close()
    
    def handle_camera(self, conn, client_id):
        """Обработка потока от камеры"""
        self.clients[client_id] = conn
        
        try:
            while self.running:
                frame_data = self.receive_frame_data(conn)
                if not frame_data:
                    break
                
                # Рассылаем всем контроллерам
                for controller_id, controller_conn in list(self.controllers.items()):
                    try:
                        controller_conn.sendall(struct.pack('>I', len(frame_data)))
                        controller_conn.sendall(frame_data)
                        controller_conn.sendall(client_id.encode('utf-8').ljust(32))
                    except:
                        print(f"🎮 Контроллер отключен: {controller_id}")
                        if controller_id in self.controllers:
                            del self.controllers[controller_id]
                            
        except Exception as e:
            print(f"📹 Ошибка камеры {client_id}: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            conn.close()
            print(f"📹 Камера отключена: {client_id}")
    
    def handle_controller(self, conn, client_id):
        """Обработка контроллера"""
        self.controllers[client_id] = conn
        
        try:
            # Держим соединение активным
            while self.running:
                time.sleep(5)
                # Проверяем соединение
                conn.sendall(b"PING")
        except:
            pass
        finally:
            if client_id in self.controllers:
                del self.controllers[client_id]
            conn.close()
            print(f"🎮 Контроллер отключен: {client_id}")
    
    def receive_frame_data(self, conn):
        """Прием данных кадра"""
        try:
            size_data = conn.recv(4)
            if not size_data or len(size_data) != 4:
                return None
                
            frame_size = struct.unpack('>I', size_data)[0]
            frame_data = b''
            
            while len(frame_data) < frame_size:
                chunk = conn.recv(min(4096, frame_size - len(frame_data)))
                if not chunk:
                    return None
                frame_data += chunk
                
            return frame_data
        except:
            return None
    
    def start(self):
        """Запуск всего сервиса"""
        # Запускаем Flask в отдельном потоке
        flask_thread = Thread(target=lambda: app.run(
            host='0.0.0.0', 
            port=5000, 
            debug=False,
            threaded=True
        ))
        flask_thread.daemon = True
        flask_thread.start()
        
        # Запускаем сокет-сервер
        self.start_socket_server()

if __name__ == "__main__":
    print("✅ Инициализация Video Hub Server...")
    server = RenderVideoHub()
    server.start()
