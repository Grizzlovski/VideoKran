import tkinter as tk
from tkinter import ttk, messagebox, StringVar
from yt_dlp import YoutubeDL
import threading

class VideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Видео Downloader (YouTube + RuTube + vkvideo.ru)")
        self.root.geometry("600x280")
        self.root.resizable(False, False)

        # Флаг для отслеживания активной загрузки
        self.downloading = False

        # Создаём фрейм для содержимого
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Поле для ввода ссылки
        ttk.Label(main_frame, text="Ссылка на видео (YouTube/RuTube/vkvideo.ru):").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5)
        )
        self.url_entry = ttk.Entry(main_frame, width=60)
        self.url_entry.grid(row=1, column=0, columnspan=2, pady=(0, 15), sticky=(tk.W, tk.E))

        # Выбор платформы
        ttk.Label(main_frame, text="Платформа:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.platform_var = StringVar(value="youtube")
        platform_frame = ttk.Frame(main_frame)
        platform_frame.grid(row=3, column=0, columnspan=2, pady=(0, 15), sticky=tk.W)

        ttk.Radiobutton(platform_frame, text="YouTube", variable=self.platform_var, value="youtube").pack(side=tk.LEFT)
        ttk.Radiobutton(platform_frame, text="RuTube", variable=self.platform_var, value="rutube").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(platform_frame, text="vkvideo.ru", variable=self.platform_var, value="vkvideo").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(platform_frame, text="other", variable=self.platform_var, value="other").pack(side=tk.LEFT, padx=(10, 0))

        # Кнопка загрузки
        self.download_btn = ttk.Button(
            main_frame,
            text="Загрузить",
            command=self.start_download
        )
        self.download_btn.grid(row=4, column=0, pady=10)

        # Прогресс-бар
        self.progress = ttk.Progressbar(
            main_frame,
            orient=tk.HORIZONTAL,
            length=500,
            mode='determinate'
        )
        self.progress.grid(row=5, column=0, columnspan=2, pady=10)

        # Статусная строка
        self.status_label = ttk.Label(main_frame, text="Готов к загрузке")
        self.status_label.grid(row=6, column=0, columnspan=2, pady=(10, 0))

    def on_progress(self, data):
        """Обновляет прогресс-бар во время загрузки"""
        try:
            if data['status'] == 'downloading':
                # Получаем размеры в байтах
                total = data.get('total_bytes') or data.get('total_bytes_estimate', 0)
                downloaded = data.get('downloaded_bytes', 0)

                # Безопасный расчёт прогресса
                if total and total > 0:
                    progress = min((downloaded / total) * 100, 100)  # Ограничиваем до 100%
                else:
                    # Если общий размер неизвестен, показываем индикатор активности
                    self.root.after(0, self._update_status, "Загрузка... (размер неизвестен)")
                    return

                # Планируем обновление интерфейса
                self.root.after(
                    100,  # Задержка 100 мс — баланс между отзывчивостью и нагрузкой
                    self._update_progress,
                    progress,
                    downloaded,
                    total
                )
            elif data['status'] == 'finished':
                self.root.after(0, self._update_status, "Завершение загрузки...")
        except Exception as e:
            print(f"Ошибка в on_progress: {e}")  # Отладка

    def _update_progress(self, progress, downloaded, total):
        """Безопасное обновление прогресс-бара и статуса"""
        # Обновляем прогресс-бар
        self.progress['value'] = max(0, min(progress, 100))  # Гарантируем диапазон 0–100%
        # Форматируем размеры в МБ
        downloaded_mb = downloaded / 1024 / 1024
        total_mb = total / 1024 / 1024 if total > 0 else 0
        # Обновляем статусную строку
        if total > 0:
            self.status_label.config(
                text=f"Прогресс: {progress:.1f}% ({downloaded_mb:.1f}MB/{total_mb:.1f}MB)"
            )
        else:
            self.status_label.config(text=f"Загружено: {downloaded_mb:.1f}MB (размер неизвестен)")
        # Принудительно обновляем интерфейс
        self.root.update_idletasks()


    def _update_status(self, status_text):
        """Безопасное обновление статусной строки"""
        self.status_label.config(text=status_text)

    def _download_complete(self, title):
        """Вызывается при успешной загрузке"""
        self.status_label.config(text="Загрузка завершена!")
        self.download_btn.config(state='normal')
        self.downloading = False
        messagebox.showinfo("Успех", f"Видео успешно скачано:\n{title}")


    def _download_failed(self, error_msg):
        """Вызывается при ошибке загрузки"""
        self.status_label.config(text="Ошибка")
        self.download_btn.config(state='normal')
        self.downloading = False
        messagebox.showerror("Ошибка", f"Произошла ошибка при загрузке:\n{error_msg}")

    def validate_url(self, url, platform):
        """Проверяет корректность URL для выбранной платформы"""
        if not url:
            return False, "Пожалуйста, введите ссылку на видео"

        if platform == "youtube" and "youtube.com" not in url and "youtu.be" not in url:
            return False, "Для YouTube введите корректную ссылку"
        elif platform == "rutube" and "rutube.ru" not in url:
            return False, "Для RuTube введите корректную ссылку"
        elif platform == "vkvideo" and "vkvideo.ru" not in url:
            return False, "Для vkvideo.ru введите корректную ссылку"

        return True, ""

    def download_video(self):
        """Выполняет загрузку видео в отдельном потоке"""
        url = self.url_entry.get().strip()
        platform = self.platform_var.get()

        try:
            # Настройки для yt-dlp
            ydl_opts = {
            'progress_hooks': [self.on_progress],
            'outtmpl': '%(title)s.%(ext)s',
            'format': 'best[height<=1080]'  # Ограничиваем до 1080p
            }

            with YoutubeDL(ydl_opts) as ydl:
                # Получаем информацию о видео (без скачивания)
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Неизвестно')

                # Обновляем статус в основном потоке
                self.root.after(0, self._update_status, f"Загрузка: {title}")


                # Начинаем загрузку
                ydl.download([url])

                # Завершение загрузки — уведомляем основной поток
                self.root.after(0, self._download_complete, title)

        except Exception as e:
            error_msg = str(e)
            # Уточняем сообщение об ошибке
            if "unavailable" in error_msg.lower():
                error_msg = "Видео недоступно или приватное"
            elif "region" in error_msg.lower():
                error_msg = "Видео ограничено по региону"
            elif "copyright" in error_msg.lower():
                error_msg = "Видео заблокировано из‑за авторских прав"

            # Уведомляем основной поток об ошибке
            self.root.after(0, self._download_failed, error_msg)

    def start_download(self):
        """Запускает процесс загрузки видео в отдельном потоке"""
        # Проверяем, идёт ли уже загрузка — предотвращаем параллельные загрузки
        if self.downloading:
            return


        # Получаем данные из интерфейса
        url = self.url_entry.get().strip()
        platform = self.platform_var.get()

        # Валидация URL для выбранной платформы
        is_valid, error_msg = self.validate_url(url, platform)
        if not is_valid:
            messagebox.showerror("Ошибка", error_msg)
            return

        # Блокируем кнопку загрузки, чтобы пользователь не мог запустить несколько загрузок
        self.download_btn.config(state='disabled')
    
        # Сбрасываем прогресс-бар
        self.progress['value'] = 0
        # Обновляем статус
        self.status_label.config(text="Подключение к сервису...")
        # Устанавливаем флаг активной загрузки
        self.downloading = True

        # Запускаем загрузку в отдельном потоке, чтобы не блокировать интерфейс
        download_thread = threading.Thread(target=self.download_video)
        download_thread.daemon = True  # Поток завершится при закрытии приложения
        download_thread.start()

def main():
    root = tk.Tk()
    app = VideoDownloader(root)
    root.mainloop()

if __name__ == "__main__":
    main()
