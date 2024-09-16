from tkinter import *
from chat import get_response, bot_name
from PIL import Image, ImageTk
import pyttsx3
import speech_recognition as sr
import logging
import uuid

BG_GRAY = "#ABB2B9"
BG_COLOR = "#17202A"
TEXT_COLOR = "#EAECEE"

FONT = ("Helvetica", 14)
FONT_BOLD = ("Helvetica", 13, "bold")

# Initialiser le moteur de synthèse vocale
engine = pyttsx3.init()

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChatApplication:
    
    def __init__(self):
        self.window = Tk()
        self._setup_main_window()
        self.user_id = str(uuid.uuid4())  # Générer un user_id unique pour la session
        
    def run(self):
        self.window.mainloop()
        
    def _setup_main_window(self):
        self.window.title("Assistant Hôtelier")
        self.window.resizable(width=False, height=False)
        self.window.configure(width=600, height=700, bg=BG_COLOR)
        
        # Charger le logo de l'hôtel
        try:
            logo = Image.open("hotel_logo.png")
            if hasattr(Image, 'Resampling'):
                resample = Image.Resampling.LANCZOS
            else:
                resample = Image.ANTIALIAS

            logo = logo.resize((100, 100), resample)
            self.logo_img = ImageTk.PhotoImage(logo)
            logo_label = Label(self.window, image=self.logo_img, bg=BG_COLOR)
            logo_label.place(x=250, y=10)
        except FileNotFoundError:
            logging.error("Le fichier 'hotel_logo.png' est introuvable.")
            logo_label = Label(self.window, text="Logo Hôtelier", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_BOLD)
            logo_label.place(x=250, y=10)
        
        head_label = Label(self.window, bg=BG_COLOR, fg=TEXT_COLOR,
                           text="Bienvenue à l'Hôtel", font=FONT_BOLD, pady=10)
        head_label.place(relwidth=1, rely=0.15)
        
        line = Label(self.window, width=450, bg=BG_GRAY)
        line.place(relwidth=1, rely=0.25, relheight=0.012)
        
        self.text_widget = Text(self.window, width=20, height=2, bg=BG_COLOR, fg=TEXT_COLOR,
                                font=FONT, padx=5, pady=5)
        self.text_widget.place(relheight=0.6, relwidth=1, rely=0.26)
        self.text_widget.configure(cursor="arrow", state=DISABLED)
        
        scrollbar = Scrollbar(self.text_widget)
        scrollbar.place(relheight=1, relx=0.974)
        scrollbar.configure(command=self.text_widget.yview)
        
        bottom_label = Label(self.window, bg=BG_GRAY, height=80)
        bottom_label.place(relwidth=1, rely=0.87)
        
        self.msg_entry = Entry(bottom_label, bg="#2C3E50", fg=TEXT_COLOR, font=FONT)
        self.msg_entry.place(relwidth=0.68, relheight=0.06, rely=0.008, relx=0.011)
        self.msg_entry.focus()
        self.msg_entry.bind("<Return>", self._on_enter_pressed)
        
        send_button = Button(bottom_label, text="Envoyer", font=FONT_BOLD, width=10, bg=BG_GRAY,
                             command=lambda: self._on_enter_pressed(None))
        send_button.place(relx=0.7, rely=0.008, relheight=0.06, relwidth=0.15)
        
        voice_button = Button(bottom_label, text="Parler", font=FONT_BOLD, width=10, bg=BG_GRAY,
                              command=self._on_voice_input)
        voice_button.place(relx=0.86, rely=0.008, relheight=0.06, relwidth=0.13)
     
    def _on_enter_pressed(self, event):
        msg = self.msg_entry.get().strip()
        if msg:
            self._insert_message(msg, "Vous")
    
    def _insert_message(self, msg, sender):
        if not msg:
            return
        
        self.msg_entry.delete(0, END)
        msg1 = f"{sender}: {msg}\n"
        self.text_widget.configure(state=NORMAL)
        self.text_widget.insert(END, msg1)
        self.text_widget.configure(state=DISABLED)
        
        try:
            response = get_response(msg, self.user_id)
        except Exception as e:
            logging.error(f"Erreur lors de la génération de la réponse : {e}")
            response = "Désolé, une erreur est survenue. Veuillez réessayer plus tard."
        
        msg2 = f"{bot_name}: {response}\n"
        self.text_widget.configure(state=NORMAL)
        self.text_widget.insert(END, msg2)
        self.text_widget.configure(state=DISABLED)
        
        if response:
            try:
                engine.say(response)
                engine.runAndWait()
            except Exception as e:
                logging.error(f"Erreur lors de la synthèse vocale : {e}")
        
        self.text_widget.see(END)
    
    def _on_voice_input(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            self.text_widget.configure(state=NORMAL)
            self.text_widget.insert(END, "Assistant: J'écoute...\n")
            self.text_widget.configure(state=DISABLED)
            self.text_widget.see(END)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                msg = recognizer.recognize_google(audio, language='fr-FR')
                self._insert_message(msg, "Vous")
            except sr.WaitTimeoutError:
                self._insert_message("Assistant: Temps d'écoute dépassé.", "Assistant")
            except sr.UnknownValueError:
                self._insert_message("Assistant: Je n'ai pas compris.", "Assistant")
            except sr.RequestError as e:
                self._insert_message(f"Assistant: Erreur du service de reconnaissance vocale; {e}", "Assistant")
            except Exception as e:
                logging.error(f"Erreur lors de la reconnaissance vocale : {e}")
                self._insert_message("Assistant: Une erreur est survenue lors de la reconnaissance vocale.", "Assistant")

if __name__ == "__main__":
    app = ChatApplication()
    app.run()
