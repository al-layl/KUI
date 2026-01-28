import tkinter as tk
from tkinter import messagebox
import os
import zipfile
from ebooklib import epub, ITEM_DOCUMENT, ITEM_IMAGE
from bs4 import BeautifulSoup
from PIL import Image, ImageTk, ImageOps
import io
import base64

class KindleApp:
    def __init__(self, root):
        self.root = root
        self.books = []  # To hold the list of books
        self.book_buttons = []  # Button widgets for books
        self.selected_idx = 0  # Start on the first book
        self.is_reading = False
        self.current_book = None
        self.spine_items = []
        self.current_page = 0
        self.current_epub_path = None
        self.note_file = "book_progress.txt"  # File to save progress
        self.current_image = None  # To hold the current displayed image
        
        # UI Setup - Physical display is 800x480, but we render at 480x800 and rotate
        self.root.title("Kindle-like eReader")
        self.root.geometry("800x480")
        self.root.resizable(False, False)  # Fixed size
        
        # Set colors
        self.bg_color = "#f5f5f5"  # Light gray background
        self.text_color = "#333333"  # Dark gray text
        self.accent_color = "#2c3e50"  # Dark blue accent
        self.hover_color = "#34495e"  # Slightly lighter blue for hover
        self.reading_bg = "#000000"  # Black for reading mode
        
        self.root.config(bg=self.bg_color)

        # Create a container canvas that will hold our rotated content
        self.rotation_canvas = tk.Canvas(self.root, width=800, height=480, 
                                        bg=self.bg_color, highlightthickness=0)
        self.rotation_canvas.pack(fill="both", expand=True)

        # Create a frame that will be rendered at 480x800 (portrait)
        # This frame will be captured as an image and rotated
        self.content_frame = tk.Frame(self.root, width=480, height=800, bg=self.bg_color)
        self.content_frame.place(x=-1000, y=-1000)  # Place off-screen

        # Create main frames inside content_frame
        self.library_frame = tk.Frame(self.content_frame, width=480, height=800, bg=self.bg_color)
        self.reading_frame = tk.Frame(self.content_frame, width=480, height=800, bg=self.reading_bg)
        
        # Initially show library frame
        self.library_frame.pack(fill="both", expand=True)
        self.reading_frame.pack_forget()
        
        # Setup Library UI
        self.setup_library_ui()
        
        # Setup Reading UI
        self.setup_reading_ui()

        # Debug: Check if library exists
        book_library = r"C:\Users\harit\KUI\library"
        if not os.path.exists(book_library):
            self.show_error(f"Library path doesn't exist: {book_library}")
        else:
            print(f"Library found at: {book_library}")

        # Load library
        self.check_books()

        # One key handler for everything (U/D/S)
        self.root.bind("<Key>", self.on_key)
        
        # Schedule the first rotation update
        self.root.after(100, self.update_rotated_display)

    def setup_library_ui(self):
        """Setup the library/user interface in portrait (480x800)"""
        # Title label at the top
        title_label = tk.Label(self.library_frame, 
                              text="My Library", 
                              font=("Helvetica", 24, "bold"), 
                              fg=self.accent_color,
                              bg=self.bg_color)
        title_label.pack(pady=(20, 5))
        
        # Subtitle
        subtitle_label = tk.Label(self.library_frame,
                                 text="Select a book to read",
                                 font=("Helvetica", 12),
                                 fg=self.text_color,
                                 bg=self.bg_color)
        subtitle_label.pack(pady=(0, 20))
        
        # Create a frame for book list with scrollbar
        list_container = tk.Frame(self.library_frame, bg=self.bg_color)
        list_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Add vertical scrollbar
        scrollbar = tk.Scrollbar(list_container, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        
        # Create canvas for book list
        self.book_canvas = tk.Canvas(list_container, bg=self.bg_color, 
                                    yscrollcommand=scrollbar.set,
                                    highlightthickness=0)
        self.book_canvas.pack(side="left", fill="both", expand=True)
        
        scrollbar.config(command=self.book_canvas.yview)
        
        # Frame inside canvas for book buttons
        self.book_frame = tk.Frame(self.book_canvas, bg=self.bg_color)
        self.book_window = self.book_canvas.create_window((0, 0), window=self.book_frame, anchor="nw")
        
        # Instructions at bottom
        instructions_label = tk.Label(self.library_frame,
                                     text="U/D: Navigate | Enter/S: Read | Click: Select",
                                     font=("Helvetica", 10),
                                     fg="#7f8c8d",
                                     bg=self.bg_color)
        instructions_label.pack(pady=(10, 10))
        
        # Error label at bottom
        self.error_label = tk.Label(self.library_frame, text="", 
                                   font=("Helvetica", 10), 
                                   fg="#e74c3c", bg=self.bg_color)
        self.error_label.pack(pady=(0, 10))
        
        # Bind canvas resize
        self.book_frame.bind("<Configure>", self.on_frame_configure)
        self.book_canvas.bind("<Configure>", self.on_canvas_configure)

    def setup_reading_ui(self):
        """Setup the reading interface in portrait (480x800)"""
        # Create canvas for reading
        self.reading_canvas = tk.Canvas(self.reading_frame, bg=self.reading_bg, 
                                       highlightthickness=0,
                                       width=480, height=800)
        self.reading_canvas.pack(fill="both", expand=True)

    def update_rotated_display(self):
        """Capture the content frame and display it rotated 90 degrees clockwise"""
        try:
            # Update the content frame to ensure everything is rendered
            self.content_frame.update_idletasks()
            
            # Get the dimensions
            x = self.content_frame.winfo_rootx()
            y = self.content_frame.winfo_rooty()
            width = self.content_frame.winfo_width()
            height = self.content_frame.winfo_height()
            
            # Clear the rotation canvas
            self.rotation_canvas.delete("all")
            
            # Create a simple colored rectangle as placeholder
            # (In production, you'd capture and rotate the actual frame)
            # For now, we'll just recreate the UI in landscape orientation
            self.render_landscape_ui()
            
        except Exception as e:
            print(f"Error updating rotated display: {e}")
        
        # Schedule next update
        self.root.after(50, self.update_rotated_display)

    def render_landscape_ui(self):
        """Render the UI in landscape orientation (800x480)"""
        if self.is_reading:
            self.render_reading_mode_landscape()
        else:
            self.render_library_mode_landscape()

    def render_library_mode_landscape(self):
        """Render library in landscape (rotated 90° clockwise from portrait)"""
        # Clear canvas
        self.rotation_canvas.delete("all")
        self.rotation_canvas.config(bg=self.bg_color)
        
        # Title (was at top, now on left side)
        self.rotation_canvas.create_text(60, 240, text="My Library", 
                                        font=("Helvetica", 24, "bold"),
                                        fill=self.accent_color, angle=90)
        
        # Subtitle
        self.rotation_canvas.create_text(100, 240, text="Select a book to read",
                                        font=("Helvetica", 12),
                                        fill=self.text_color, angle=90)
        
        # Book list (center area) - need to rotate the entire button area
        start_x = 150
        button_width = 60
        button_height = 500
        
        for idx, book_name in enumerate(self.books):
            x_pos = start_x + (idx * 70)
            
            # Determine colors based on selection
            if idx == self.selected_idx:
                bg = self.accent_color
                fg = "white"
            else:
                bg = "white"
                fg = self.text_color
            
            # Create button background (tall and narrow for rotated layout)
            rect = self.rotation_canvas.create_rectangle(x_pos, 40, x_pos + button_width, 440,
                                                        fill=bg, outline="", tags=f"book_{idx}")
            
            # Create button text rotated 90° (clockwise)
            text = self.rotation_canvas.create_text(x_pos + 30, 240, text=book_name,
                                                   font=("Helvetica", 12),
                                                   fill=fg, tags=f"book_{idx}",
                                                   angle=90)
            
            # Bind click event
            self.rotation_canvas.tag_bind(f"book_{idx}", "<Button-1>", 
                                         lambda e, i=idx: self.select_book_index(i))
        
        # Instructions (was at bottom, now on right side)
        self.rotation_canvas.create_text(760, 240, 
                                        text="U/D: Navigate\nEnter/S: Read\nClick: Select",
                                        font=("Helvetica", 10),
                                        fill="#7f8c8d", angle=90)
        
        # Error message if any
        if self.error_label.cget("text"):
            self.rotation_canvas.create_text(720, 240, text=self.error_label.cget("text"),
                                            font=("Helvetica", 10),
                                            fill="#e74c3c", angle=90)

    def render_reading_mode_landscape(self):
        """Render reading mode in landscape"""
        # Clear canvas
        self.rotation_canvas.delete("all")
        self.rotation_canvas.config(bg=self.reading_bg)
        
        if not self.spine_items:
            return
        
        try:
            item = self.spine_items[self.current_page]
            soup = BeautifulSoup(item.content, "html.parser")
            
            # Page info (left side)
            page_text = f"Page {self.current_page + 1} of {len(self.spine_items)}"
            self.rotation_canvas.create_text(40, 240, text=page_text,
                                           font=("Helvetica", 12),
                                           fill="#ecf0f1", angle=90)
            
            # Check for images
            images = soup.find_all('img')
            
            if images:
                self.display_page_image_landscape(soup, item)
            else:
                self.display_page_text_landscape(soup)
            
            # Instructions (right side)
            self.rotation_canvas.create_text(760, 240,
                                           text="U/D: Previous/Next\nS/Esc: Back to Library",
                                           font=("Helvetica", 10),
                                           fill="#7f8c8d", angle=90)
            
        except Exception as e:
            print(f"Page display error: {e}")

    def display_page_image_landscape(self, soup, item):
        """Display image in landscape mode"""
        try:
            images = soup.find_all('img')
            img_found = False
            
            for img_tag in images:
                src = img_tag.get('src', '')
                if not src:
                    continue
                    
                img_data = self.extract_image_from_epub(src)
                
                if img_data:
                    image = Image.open(io.BytesIO(img_data))
                    
                    # Rotate image 90° counterclockwise to match text orientation
                    image = image.rotate(90, expand=True)
                    
                    # Scale to fit
                    target_width = 600
                    target_height = 400
                    
                    img_width, img_height = image.size
                    scale = min(target_width / img_width, target_height / img_height)
                    
                    if scale < 1:
                        new_size = (int(img_width * scale), int(img_height * scale))
                        image = image.resize(new_size, Image.Resampling.LANCZOS)
                    
                    photo = ImageTk.PhotoImage(image)
                    self.current_image = photo
                    
                    # Center on canvas
                    self.rotation_canvas.create_image(400, 240, image=photo)
                    img_found = True
                    break
            
            if not img_found:
                # Try ZIP extraction
                try:
                    with zipfile.ZipFile(self.current_epub_path, 'r') as epub_zip:
                        for file_info in epub_zip.infolist():
                            if file_info.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                img_data = epub_zip.read(file_info.filename)
                                image = Image.open(io.BytesIO(img_data))
                                image = image.rotate(90, expand=True)
                                
                                target_width = 600
                                target_height = 400
                                img_width, img_height = image.size
                                scale = min(target_width / img_width, target_height / img_height)
                                
                                if scale < 1:
                                    new_size = (int(img_width * scale), int(img_height * scale))
                                    image = image.resize(new_size, Image.Resampling.LANCZOS)
                                
                                photo = ImageTk.PhotoImage(image)
                                self.current_image = photo
                                self.rotation_canvas.create_image(400, 240, image=photo)
                                img_found = True
                                break
                except Exception as e:
                    print(f"Error extracting from ZIP: {e}")
            
            if not img_found:
                self.display_page_text_landscape(soup)
                
        except Exception as e:
            print(f"Image display error: {e}")

    def display_page_text_landscape(self, soup):
        """Display text in landscape mode with 90° rotation"""
        # Clean HTML
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if not text:
            text = "(No readable content on this page)"
        
        # Display text rotated 90° in center
        self.rotation_canvas.create_text(400, 240, text=text,
                                        font=("Helvetica", 14),
                                        fill="#ecf0f1",
                                        angle=90, width=400)

    def on_frame_configure(self, event=None):
        """Reset the scroll region to encompass the inner frame"""
        self.book_canvas.configure(scrollregion=self.book_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Reset the canvas window width"""
        self.book_canvas.itemconfig(self.book_window, width=event.width)

    # ---------- Error Handling ----------
    def show_error(self, msg: str):
        self.error_label.config(text=msg)
        print(f"ERROR: {msg}")

    def clear_error(self):
        self.error_label.config(text="")

    # ---------- Progress Management ----------
    def load_progress(self, epub_path: str) -> int:
        if not os.path.exists(self.note_file):
            return 0

        try:
            with open(self.note_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or "\t" not in line:
                        continue
                    path, page = line.split("\t", 1)
                    if path == epub_path:
                        try:
                            return int(page)
                        except ValueError:
                            return 0
        except Exception as e:
            print(f"Error loading progress: {e}")
            return 0

        return 0

    def save_progress(self, epub_path: str, page: int):
        if not epub_path:
            return
            
        rows = {}
        if os.path.exists(self.note_file):
            try:
                with open(self.note_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or "\t" not in line:
                            continue
                        path, pg = line.split("\t", 1)
                        rows[path] = pg
            except Exception as e:
                print(f"Error reading progress file: {e}")
                rows = {}

        rows[epub_path] = str(page)

        try:
            with open(self.note_file, "w", encoding="utf-8") as f:
                for path, pg in rows.items():
                    f.write(f"{path}\t{pg}\n")
        except Exception as e:
            print(f"Error saving progress: {e}")

    # ---------- Library Management ----------
    def check_books(self):
        book_library = r"C:\Users\harit\KUI\library"
        
        try:
            self.books = [book for book in os.listdir(book_library) 
                         if os.path.isdir(os.path.join(book_library, book))]
        except FileNotFoundError:
            self.show_error("Library folder not found!")
            self.books = []
            return
        
        print(f"Found books: {self.books}")
        
        if not self.books:
            self.show_error("No books found in library!")
            return
        
        for widget in self.book_frame.winfo_children():
            widget.destroy()

        self.book_buttons = []
        for idx, book in enumerate(self.books):
            self.create_book_button(book, idx)
        
        if self.book_buttons:
            self.update_library_highlight()

    def create_book_button(self, book_name, idx):
        """Create a book button"""
        button = tk.Button(self.book_frame, text=book_name,
                          font=("Helvetica", 12),
                          bg="white", fg=self.text_color,
                          relief="flat", borderwidth=0,
                          padx=20, pady=15,
                          anchor="w",
                          command=lambda: self.select_book_index(idx))
        button.pack(fill="x", padx=10, pady=5)
        
        self.book_buttons.append(button)
        return button

    def select_book_index(self, idx):
        """Select a book by index"""
        self.selected_idx = idx
        self.update_library_highlight()
        
        if self.is_reading:
            book_name = self.books[idx]
            self.open_epub(book_name)

    def update_library_highlight(self):
        """Update button highlights in library"""
        for i, button in enumerate(self.book_buttons):
            if i == self.selected_idx:
                button.config(bg=self.accent_color, fg="white")
            else:
                button.config(bg="white", fg=self.text_color)

    # ---------- Reading Functions ----------
    def open_epub(self, book_name):
        """Open an EPUB file"""
        book_path = os.path.join(r"C:\Users\harit\KUI\library", book_name)
        
        epub_file = None
        for file in os.listdir(book_path):
            if file.endswith(".epub"):
                epub_file = file
                break
        
        if epub_file:
            self.load_epub(os.path.join(book_path, epub_file))
        else:
            self.show_error("No EPUB file found")
            self.exit_reading_mode()
    
    def load_epub(self, epub_file_path):
        """Load an EPUB file"""
        try:
            print(f"Loading EPUB: {epub_file_path}")
            book = epub.read_epub(epub_file_path)
            items = list(book.get_items_of_type(ITEM_DOCUMENT))
            
            print(f"Found {len(items)} document sections")

            if not items:
                self.show_error("EPUB has no readable content")
                return

            self.current_epub_path = epub_file_path
            self.current_book = book
            self.spine_items = items
            self.current_page = self.load_progress(epub_file_path)
            self.current_page = max(0, min(self.current_page, len(self.spine_items) - 1))
            self.is_reading = True

            self.library_frame.pack_forget()
            self.reading_frame.pack(fill="both", expand=True)

            self.display_current_page()

        except Exception as e:
            self.show_error(f"Error opening book: {e}")
            print(f"Detailed error: {str(e)}")
            self.exit_reading_mode()

    def display_current_page(self):
        """Display the current page"""
        if not self.is_reading or not self.spine_items:
            return

        try:
            self.save_progress(self.current_epub_path, self.current_page)
        except Exception as e:
            print(f"Page display error: {e}")

    def extract_image_from_epub(self, img_src):
        """Extract image data from EPUB"""
        try:
            img_src = img_src.lstrip('/').replace('../', '')
            
            for item in self.current_book.get_items():
                if hasattr(item, 'get_name') and item.get_name():
                    item_name = item.get_name()
                    if img_src in item_name or item_name.endswith(img_src):
                        return item.get_content()
            
            for i, spine_item in enumerate(self.spine_items):
                if i == self.current_page:
                    soup = BeautifulSoup(spine_item.content, 'html.parser')
                    img_tags = soup.find_all('img')
                    
                    for img_tag in img_tags:
                        src = img_tag.get('src', '')
                        if 'data:' in src and 'base64' in src:
                            data = src.split('base64,')[1]
                            return base64.b64decode(data)
            
            return None
            
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None

    # ---------- Navigation ----------
    def page_up(self):
        if self.is_reading and self.current_page > 0:
            self.current_page -= 1
            self.display_current_page()

    def page_down(self):
        if self.is_reading and self.current_page < len(self.spine_items) - 1:
            self.current_page += 1
            self.display_current_page()

    def enter_reading_mode(self):
        """Enter reading mode with selected book"""
        if not self.books or self.selected_idx >= len(self.books):
            self.show_error("No book selected!")
            return
        
        book_name = self.books[self.selected_idx]
        self.open_epub(book_name)

    def exit_reading_mode(self):
        """Exit reading mode and return to library"""
        if self.current_epub_path and self.is_reading:
            self.save_progress(self.current_epub_path, self.current_page)
        
        self.is_reading = False
        self.current_book = None
        self.spine_items = []
        self.current_page = 0
        self.current_epub_path = None
        self.current_image = None
        
        self.reading_frame.pack_forget()
        self.library_frame.pack(fill="both", expand=True)
        
        self.clear_error()
        
        print("Returned to library")

    # ---------- Key Handling ----------
    def on_key(self, event):
        ch = (event.char or "").upper()
        
        if ch in ("U", "D", "S", "\r"):
            self.clear_error()

        if ch == "S" or ch == "\r" or event.keysym == "Escape":
            if self.is_reading:
                self.exit_reading_mode()
            else:
                self.enter_reading_mode()
            return

        if ch == "U" or event.keysym == "Up":
            if self.is_reading:
                self.page_up()
            else:
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                    self.update_library_highlight()
            return

        if ch == "D" or event.keysym == "Down":
            if self.is_reading:
                self.page_down()
            else:
                if self.selected_idx < len(self.book_buttons) - 1:
                    self.selected_idx += 1
                    self.update_library_highlight()
            return


if __name__ == "__main__":
    root = tk.Tk()
    app = KindleApp(root)
    root.mainloop()
