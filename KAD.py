import os
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import json

# Variable pour contrôler l'arrêt du téléchargement
stop_download_flag = False

# Chemin vers le fichier de configuration
config_file_path = 'config.json'

# Traductions ajoutées
translations = {
    "fr": {
        "window_title": "Kenney Assets Downloader",
        "start_download": "Démarrer le téléchargement",
        "stop_download": "Arrêter le téléchargement",
        "downloading": "Téléchargement de :",
        "total_files_downloaded": "Total des fichiers téléchargés :",
        "total_pages": "Nombre total de pages :",
        "searching": "Recherche en cours",
        "language": "Langage "
    },
    "en": {
        "window_title": "Kenney Assets Downloader",
        "start_download": "Start Download",
        "stop_download": "Stop Download",
        "downloading": "Downloading:",
        "total_files_downloaded": "Total Files Downloaded:",
        "total_pages": "Total Pages:",
        "searching": "Searching",
        "language": "Language "
    }
}

# Fonction pour charger la configuration
def load_config():
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as config_file:
            return json.load(config_file)
    return {"language": "fr"}

# Fonction pour sauvegarder la configuration
def save_config(config):
    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file)

# Charger la configuration
config = load_config()
current_language = config.get("language", "fr")

# Fonction pour obtenir la traduction
def translate(key):
    return translations[current_language].get(key, key)

def get_zip_links(detail_page_url):
    response = requests.get(detail_page_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    zip_links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.zip')]
    return zip_links

def download_file(url, dest_folder, update_status, update_current_file):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    local_filename = os.path.join(dest_folder, url.split('/')[-1])
    update_current_file(url.split('/')[-1])  # Afficher uniquement le nom du fichier
    update_status(f"{translate('downloading')} {url}...", bold=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    update_current_file("")
    return local_filename

def get_detail_page_links(page_url):
    response = requests.get(page_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    detail_links = []
    for a in soup.find_all('a', href=True):
        link = a['href']
        if '/assets/' in link and not link.startswith('/assets/category') and not link.startswith('/assets/tag'):
            full_link = "https://kenney.nl" + link if not link.startswith('http') else link
            detail_links.append(full_link)
    return detail_links

def get_total_pages(base_url):
    page_num = 1
    while True:
        page_url = base_url + str(page_num)
        response = requests.get(page_url)
        if response.status_code != 200 or 'No results found' in response.text:
            break
        page_num += 1
    return page_num - 1

def download_assets(update_status, update_progress, update_total, update_current_file):
    global stop_download_flag
    base_url = 'https://kenney.nl/assets/page:'
    num_pages = get_total_pages(base_url)
    total_downloaded = 0
    downloaded_links = set()

    update_status(f"{translate('total_pages')} {num_pages}")
    total_pages_var.set(f"{translate('total_pages')} {num_pages}")
    
    for page_num in range(1, num_pages + 1):
        if stop_download_flag:
            update_status(translate("stopped"))
            break
        page_url = base_url + str(page_num)
        update_status(f"{translate('accessing_page')} {page_url}")
        detail_links = get_detail_page_links(page_url)

        for detail_link in detail_links:
            if stop_download_flag:
                update_status(translate("stopped"))
                break
            if detail_link not in downloaded_links:
                zip_links = get_zip_links(detail_link)
                if not zip_links:
                    update_status(translate("searching"), bold=True)
                else:
                    update_status(f"{translate('accessing_details')} {detail_link}")

                for link in zip_links:
                    if stop_download_flag:
                        update_status(translate("stopped"))
                        break
                    if link not in downloaded_links:
                        local_filename = download_file(link, script_dir, update_status, update_current_file)
                        total_downloaded += 1
                        downloaded_links.add(link)
                        update_progress(total_downloaded)
                        update_total(total_downloaded)

    if not stop_download_flag:
        update_status(translate("completed"))
    stop_download_flag = False
    progress_bar.stop()
    progress_bar['value'] = 0
    progress_bar.config(mode='determinate')

def start_download():
    global stop_download_flag
    stop_download_flag = False
    download_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    total_var.set(f"{translate('total_files_downloaded')} 0")
    total_pages_var.set(f"{translate('total_pages')} {translate('searching')}")
    current_file_var.set(f"{translate('downloading')} ")
    progress_bar.config(mode='indeterminate', maximum=50)  # Changer le mode pour l'animation et élargir la barre de progression
    progress_bar.start()  # Lancer la barre d'animation
    status_text.delete(1.0, tk.END)  # Réinitialiser le texte du statut
    root.update()
    download_thread = threading.Thread(target=download_assets, args=(update_status, update_progress, update_total_files, update_current_file))
    download_thread.start()

def stop_download():
    global stop_download_flag
    stop_download_flag = True
    progress_bar.stop()  # Arrêter la barre d'animation
    progress_bar.config(mode='determinate')  # Changer le mode pour le rendre complètement vide
    progress_bar['value'] = 0  # Réinitialiser la barre de progression
    current_file_var.set(f"{translate('downloading')} ")
    download_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)

def update_status(message, bold=False):
    status_text.tag_configure('bold', font=('Helvetica', 10, 'bold'))
    if bold:
        status_text.insert(tk.END, message + '\n', 'bold')
    else:
        status_text.insert(tk.END, message + '\n')
    status_text.see(tk.END)
    root.update()

def update_progress(total):
    progress_bar.step(1)
    root.update()

def update_total_files(total):
    total_var.set(f"{translate('total_files_downloaded')} {total}")
    root.update()

def update_current_file(filename):
    if filename:
        current_file_var.set(f"{translate('downloading')} {filename}")
    else:
        current_file_var.set(f"{translate('downloading')} {translate('searching')}")
    root.update()

def change_language(event):
    global current_language
    current_language = language_var.get()
    config["language"] = current_language
    save_config(config)
    update_ui_language()

def update_ui_language():
    root.title(translate("window_title"))
    download_button.config(text=translate("start_download"))
    stop_button.config(text=translate("stop_download"))
    current_file_var.set(f"{translate('downloading')} ")
    total_var.set(f"{translate('total_files_downloaded')} 0")
    total_pages_var.set(f"{translate('total_pages')} {translate('searching')}")
    language_label_var.set(translate("language"))

# Interface graphique
root = tk.Tk()
root.title(translate("window_title"))
root.geometry("600x500")  # Taille fixe de la fenêtre
root.resizable(False, False)  # Désactiver le redimensionnement de la fenêtre

language_label_var = tk.StringVar()
language_label = ttk.Label(root, textvariable=language_label_var)
language_label.grid(row=0, column=1, padx=(10, 0), pady=10, sticky='e')

language_var = tk.StringVar(value=current_language)
language_combobox = ttk.Combobox(root, textvariable=language_var, values=["fr", "en"])
language_combobox.grid(row=0, column=2, padx=(0, 10), pady=10, sticky='w')
language_combobox.bind("<<ComboboxSelected>>", change_language)

status_text = ScrolledText(root, wrap=tk.WORD, height=10, width=70)
status_text.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

progress_bar = ttk.Progressbar(root, length=400, mode='determinate', maximum=50)
progress_bar.grid(row=2, column=0, columnspan=3, padx=10, pady=10)

current_file_var = tk.StringVar()
current_file_label = ttk.Label(root, textvariable=current_file_var)
current_file_label.grid(row=3, column=0, columnspan=3, padx=10, pady=10)
current_file_var.set(f"{translate('downloading')} ")

total_var = tk.StringVar()
total_label = ttk.Label(root, textvariable=total_var)
total_label.grid(row=4, column=0, columnspan=3, padx=10, pady=10)
total_var.set(f"{translate('total_files_downloaded')} 0")

total_pages_var = tk.StringVar()
total_pages_label = ttk.Label(root, textvariable=total_pages_var)
total_pages_label.grid(row=5, column=0, columnspan=3, padx=10, pady=10)
total_pages_var.set(f"{translate('total_pages')} {translate('searching')}")

download_button = ttk.Button(root, text=translate("start_download"), command=start_download, width=30)
download_button.grid(row=6, column=0, padx=10, pady=20, ipady=10)

stop_button = ttk.Button(root, text=translate("stop_download"), command=stop_download, state=tk.DISABLED, width=30)
stop_button.grid(row=6, column=1, padx=10, pady=20, ipady=10)

# Obtenir le répertoire du script en cours d'exécution
script_dir = os.path.dirname(os.path.abspath(__file__))

update_ui_language()

root.mainloop()
