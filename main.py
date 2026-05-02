import threading
import certifi
import os
import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
import yt_dlp

# Certificados de segurança
os.environ['SSL_CERT_FILE'] = certifi.where()

class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class YoutubeApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Barra de Busca
        search_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=10)
        self.input_text = TextInput(hint_text='Link ou nome do vídeo...', multiline=False, font_size='18sp')
        btn_search = Button(text='BUSCAR', size_hint_x=0.3, background_color=(0.1, 0.5, 0.9, 1), bold=True)
        btn_search.bind(on_release=self.iniciar_busca)
        search_bar.add_widget(self.input_text)
        search_bar.add_widget(btn_search)
        self.root.add_widget(search_bar)

        # Status e Progresso
        self.status_global = Label(text="Aguardando...", size_hint_y=None, height='30dp')
        self.bar_global = ProgressBar(max=100, size_hint_y=None, height='15dp')
        self.root.add_widget(self.status_global)
        self.root.add_widget(self.bar_global)

        # Lista de Resultados
        self.scroll = ScrollView(do_scroll_x=False)
        self.lista = BoxLayout(orientation='vertical', size_hint_y=None, spacing=30)
        self.lista.bind(minimum_height=self.lista.setter('height'))
        self.scroll.add_widget(self.lista)
        self.root.add_widget(self.scroll)

        return self.root

    def iniciar_busca(self, *args):
        if not self.input_text.text: return
        self.lista.clear_widgets()
        self.status_global.text = "🔍 Buscando vídeos..."
        threading.Thread(target=self.fazer_busca, args=(self.input_text.text,)).start()

    def fazer_busca(self, termo):
        ydl_opts = {'quiet': True, 'logger': SilentLogger(), 'nocheckcertificate': True, 'extract_flat': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                prompt = f"ytsearch5:{termo}" if not termo.startswith('http') else termo
                info = ydl.extract_info(prompt, download=False)
                vids = info['entries'] if 'entries' in info else [info]
                Clock.schedule_once(lambda dt: self.mostrar_vids(vids))
        except Exception as e:
            err = str(e)
            Clock.schedule_once(lambda dt: self.mostrar_erro(f"Erro Busca: {err[:20]}"))

    def mostrar_vids(self, videos):
        self.lista.clear_widgets()
        self.status_global.text = "Resultados encontrados!"
        for v in videos:
            if not v: continue
            card = BoxLayout(orientation='vertical', size_hint_y=None, height='500dp', spacing=10, padding=10)
            
            # Thumbnail Fixa (HQ)
            video_id = v.get('id') or v.get('url', '').split('=')[-1]
            thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            
            card.add_widget(AsyncImage(source=thumb_url, size_hint_y=None, height='280dp', allow_stretch=True))
            card.add_widget(Label(text=v.get('title', 'Vídeo')[:60], size_hint_y=None, height='40dp', bold=True))
            
            # Botões
            btns = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=10)
            b_vid = Button(text="VÍDEO MP4", background_color=(0, 0.6, 0.3, 1), bold=True)
            b_vid.bind(on_release=lambda x, u=v.get('url') or v.get('webpage_url'): self.download(u, 'video'))
            
            b_aud = Button(text="ÁUDIO M4A", background_color=(0.7, 0.2, 0.2, 1), bold=True)
            b_aud.bind(on_release=lambda x, u=v.get('url') or v.get('webpage_url'): self.download(u, 'audio'))
            
            btns.add_widget(b_vid)
            btns.add_widget(b_aud)
            card.add_widget(btns)
            self.lista.add_widget(card)

    def download(self, url, tipo):
        self.bar_global.value = 0
        self.status_global.text = f"⬇️ Iniciando download de {tipo}..."
        threading.Thread(target=self.task_download, args=(url, tipo)).start()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%', '').strip()
            try:
                val = float(p)
                Clock.schedule_once(lambda dt: self.update_ui(val))
            except: pass
        if d['status'] == 'finished':
            Clock.schedule_once(lambda dt: self.update_ui(100, "✅ SALVO COM SUCESSO!"))

    def update_ui(self, val, txt=None):
        self.bar_global.value = val
        if txt: 
            self.status_global.text = txt
            self.status_global.color = (0, 1, 0.5, 1)
        else: 
            self.status_global.text = f"Baixando: {int(val)}%"

    def task_download(self, url, tipo):
        # CAMINHO ABSOLUTO PARA A PASTA DE DOWNLOADS DO ANDROID
        pasta_destino = '/storage/emulated/0/Download'
        
        # Limpa o título do vídeo para não ter erro de arquivo
        ydl_opts_meta = {'quiet': True, 'logger': SilentLogger(), 'nocheckcertificate': True}
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            meta = ydl.extract_info(url, download=False)
            safe_title = re.sub(r'[\\/*?:"<>|]', "", meta.get('title', 'video'))

        ext = 'mp4' if tipo == 'video' else 'm4a'
        caminho_final = os.path.join(pasta_destino, f"{safe_title}.{ext}")

        # Configurações de download
        opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if tipo == 'video' else 'bestaudio[ext=m4a]/best',
            'outtmpl': caminho_final,
            'progress_hooks': [self.progress_hook],
            'nocheckcertificate': True,
            'quiet': True,
            'logger': SilentLogger()
        }
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            err = str(e)
            Clock.schedule_once(lambda dt: self.mostrar_erro(f"Erro Down: {err[:25]}"))

    def mostrar_erro(self, msg):
        self.status_global.text = msg
        self.status_global.color = (1, 0, 0, 1)

if __name__ == '__main__':
    YoutubeApp().run()
