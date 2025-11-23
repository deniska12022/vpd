import socket
import cv2
import numpy as np
import struct
import threading
import os
import time

class RenderVideoHub:
    def __init__(self, host='0.0.0.0', port=4444):
        self.host = host
        self.port = int(os.environ.get('PORT', port))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        self.clients = {}
        self.controllers = {}
        self.running = True
        
        print(f"🚀 Video Hub запущен на {self.host}:{self.port}")
        print("📡 Ожидаем подключения...")
        
    def handle_camera_client(self, conn, addr):
        """Обработка подключения от камеры"""
        client_id = f"{addr[0]}:{addr[1]}"
        print(f"📹 Подключена камера: {client_id}")
        self.clients[client_id] = conn
        
        try:
            while self.running:
                # Получаем кадр от камеры
                frame_data = self.receive_frame_data(conn)
                if not frame_data:
                    break
                
                # Отправляем всем контроллерам
                for controller_id, controller_conn in list(self.controllers.items()):
                    try:
                        controller_conn.sendall(struct.pack('>I', len(frame_data)))
                        controller_conn.sendall(frame_data)
                        # Отправляем ID камеры
                        controller_conn.sendall(client_id.encode('utf-8').ljust(32))
                    except:
                        print(f"❌ Контроллер отключен: {controller_id}")
                        del self.controllers[controller_id]
                        
        except Exception as e:
            print(f"📹 Ошибка с камерой {client_id}: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            conn.close()
            print(f"📹 Камера отключена: {client_id}")
            
    def handle_controller_client(self, conn, addr):
        """Обработка подключения от контроллера"""
        controller_id = f"{addr[0]}:{addr[1]}"
        print(f"🎮 Подключен контроллер: {controller_id}")
        self.controllers[controller_id] = conn
        
        try:
            # Просто держим соединение активным
            while self.running:
                time.sleep(1)
                # Проверяем, что соединение живо
                conn.sendall(b"PING")
        except:
            pass
        finally:
            if controller_id in self.controllers:
                del self.controllers[controller_id]
            conn.close()
            print(f"🎮 Контроллер отключен: {controller_id}")
    
    def receive_frame_data(self, conn):
        """Прием данных кадра"""
        try:
            # Получаем размер кадра
            size_data = conn.recv(4)
            if not size_data or len(size_data) != 4:
                return None
                
            frame_size = struct.unpack('>I', size_data)[0]
            frame_data = b''
            
            # Получаем данные кадра
            while len(frame_data) < frame_size:
                chunk_size = min(4096, frame_size - len(frame_data))
                chunk = conn.recv(chunk_size)
                if not chunk:
                    return None
                frame_data += chunk
                
            return frame_data
            
        except Exception as e:
            return None
    
    def start(self):
        """Запуск сервера"""
        print("✅ Сервер запущен и готов к работе!")
        
        try:
            while self.running:
                conn, addr = self.socket.accept()
                print(f"🔗 Новое подключение от: {addr}")
                
                # Определяем тип клиента (первые 10 байт)
                try:
                    client_type_data = conn.recv(10)
                    client_type = client_type_data.decode('utf-8').strip()
                    
                    if client_type == "CAMERA":
                        thread = threading.Thread(
                            target=self.handle_camera_client, 
                            args=(conn, addr)
                        )
                    else:
                        thread = threading.Thread(
                            target=self.handle_controller_client,
                            args=(conn, addr)
                        )
                        
                    thread.daemon = True
                    thread.start()
                    
                except Exception as e:
                    print(f"❌ Ошибка определения типа клиента: {e}")
                    conn.close()
                    
        except KeyboardInterrupt:
            print("\n🛑 Сервер остановлен")
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
        finally:
            self.socket.close()

if __name__ == "__main__":
    server = RenderVideoHub()
    server.start()
