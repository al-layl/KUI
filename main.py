import tkinter as tk
from tkinter import messagebox
import os
import zipfile
from ebooklib import epub, ITEM_DOCUMENT, ITEM_IMAGE
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
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
        
        # UI Setup - Fixed 480x800 size
        self.root.title("Kindle-like eReader")
        self.root.geometry("480x800")
        self.root.resizable(False, False)  # Fixed size
        
        # Set colors
        self.bg_color = "#f5f5f5"  # Light gray background
        self.text_color = "#333333"  # Dark gray text
        self.accent_color = "#2c3e50"  # Dark blue accent
        self.hover_color = "#34495e"  # Slightly lighter blue for hover
        self.reading_bg = "#000000"  # Black for reading mode
        
        self.root.config(bg=self.bg_color)

        # Create main frames
        self.library_frame = tk.Frame(self.root, bg=self.bg_color)
        self.reading_frame = tk.Frame(self.root, bg=self.reading_bg)
        
        # Initially show library frame
        self.library_frame.pack(fill="both", expand=True)
        self.reading_frame.pack_forget()
        
        # Setup Library UI
        self.setup_library_ui()
        
        # Setup Reading UI
        self.setup_reading_ui()

        # Debug: Check if library exists
        book_library = r"E:\Projects\KUI\library"
        if not os.path.exists(book_library):
            self.show_error(f"Library path doesn't exist: {book_library}")
        else:
            print(f"Library found at: {book_library}")

        # Load library
        self.check_books()

        # One key handler for everything (U/D/S)
        self.root.bind("<Key>", self.on_key)

    def setup_library_ui(self):
        """Setup the library/user interface"""
        # Title label at the top
        title_label = tk.Label(self.library_frame, text="My Library", 
                              font=("Helvetica", 24, "bold"), 
                              bg=self.bg_color, fg=self.accent_color)
        title_label.pack(pady=10)
        
        # Subtitle
        subtitle = tk.Label(self.library_frame, text="Select a book to read", 
                           font=("Helvetica", 12), 
                           bg=self.bg_color, fg=self.text_color)
        subtitle.pack(pady=(0, 10))
        
        # Create a frame for book list with scrollbar
        list_container = tk.Frame(self.library_frame, bg=self.bg_color)
        list_container.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Add scrollbar
        scrollbar = tk.Scrollbar(list_container)
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
        
        # Bind canvas resize
        self.book_frame.bind("<Configure>", self.on_frame_configure)
        self.book_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Instructions at bottom
        instructions = tk.Label(self.library_frame, 
                               text="↑/↓: Navigate | Enter/S: Read | Click: Select",
                               font=("Helvetica", 10), 
                               bg=self.bg_color, fg="#7f8c8d")
        instructions.pack(pady=10)
        
        # Error label at bottom
        self.error_label = tk.Label(self.library_frame, text="", 
                                   font=("Helvetica", 10), 
                                   fg="#e74c3c", bg=self.bg_color)
        self.error_label.pack(pady=5)

    def setup_reading_ui(self):
        """Setup the reading interface"""
        # Create canvas for reading
        self.reading_canvas = tk.Canvas(self.reading_frame, bg=self.reading_bg, 
                                       highlightthickness=0)
        self.reading_canvas.pack(fill="both", expand=True)
        
        # Add page info at top (initially hidden)
        self.page_info = self.reading_canvas.create_text(240, 20, 
                                                        text="", 
                                                        font=("Helvetica", 12), 
                                                        fill="#ecf0f1", 
                                                        anchor="center")
        
        # Instructions at bottom
        self.reading_canvas.create_text(240, 780, 
                                       text="↑/↓: Previous/Next | S/Esc: Back to Library",
                                       font=("Helvetica", 10), 
                                       fill="#7f8c8d", 
                                       anchor="center")

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
            
        # Read all existing
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

        # Update this book
        rows[epub_path] = str(page)

        # Write back
        try:
            with open(self.note_file, "w", encoding="utf-8") as f:
                for path, pg in rows.items():
                    f.write(f"{path}\t{pg}\n")
        except Exception as e:
            print(f"Error saving progress: {e}")

    # ---------- Library Management ----------
    def check_books(self):
        book_library = r"E:\Projects\KUI\library"
        
        try:
            self.books = [book for book in os.listdir(book_library) 
                         if os.path.isdir(os.path.join(book_library, book))]
        except FileNotFoundError:
            self.show_error("Library folder not found!")
            self.books = []
            return
        
        # Debug: Print found books
        print(f"Found books: {self.books}")
        
        if not self.books:
            self.show_error("No books found in library!")
            return
        
        # Clear previous buttons if they exist
        for widget in self.book_frame.winfo_children():
            widget.destroy()

        self.book_buttons = []
        # Add buttons for each book folder
        for idx, book in enumerate(self.books):
            self.create_book_button(book, idx)
        
        # Highlight the first book initially
        if self.book_buttons:
            self.update_library_highlight()

    def create_book_button(self, book_name, idx):
        """Create a styled book button"""
        # Create frame for button with border
        button_frame = tk.Frame(self.book_frame, bg=self.bg_color)
        button_frame.pack(pady=5, padx=20, fill="x")
        
        # Create the button
        button = tk.Button(button_frame, text=book_name, 
                          font=("Helvetica", 12), 
                          bg="white", fg=self.text_color,
                          relief="flat", anchor="w",
                          padx=15, pady=10)
        
        # Style the button
        button.config(borderwidth=1, highlightthickness=0,
                      activebackground=self.hover_color, 
                      activeforeground="white")
        
        # Bind events
        button.bind("<Enter>", lambda e, b=button: self.on_button_hover(b))
        button.bind("<Leave>", lambda e, b=button: self.on_button_leave(b))
        button.config(command=lambda b=book_name, i=idx: self.select_book(b, i))
        
        button.pack(fill="x")
        
        self.book_buttons.append(button)
        
        # Return button for reference
        return button

    def on_button_hover(self, button):
        """Handle button hover"""
        if not self.is_reading:
            button.config(bg=self.hover_color, fg="white")

    def on_button_leave(self, button):
        """Handle button leave"""
        if not self.is_reading:
            idx = self.book_buttons.index(button)
            if idx == self.selected_idx:
                button.config(bg=self.accent_color, fg="white")
            else:
                button.config(bg="white", fg=self.text_color)

    def select_book(self, book_name, idx):
        """Select a book from the library"""
        self.selected_idx = idx
        self.update_library_highlight()
        
        # If already reading, open this book
        if self.is_reading:
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
        book_path = os.path.join(r"E:\Projects\KUI\library", book_name)
        
        # Find EPUB file
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

            # Switch to reading frame
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
            item = self.spine_items[self.current_page]
            soup = BeautifulSoup(item.content, "html.parser")
            
            # Clear canvas
            self.reading_canvas.delete("all")
            self.current_image = None
            
            # Update page info
            page_text = f"Page {self.current_page + 1} of {len(self.spine_items)}"
            self.reading_canvas.create_text(240, 20, 
                                           text=page_text, 
                                           font=("Helvetica", 12), 
                                           fill="#ecf0f1", 
                                           anchor="center")
            
            # Check for images
            images = soup.find_all('img')
            
            if images:
                # Display image
                self.display_page_image(soup, item)
            else:
                # Display text
                self.display_page_text(soup)
            
            # Add bottom instructions
            self.reading_canvas.create_text(240, 780, 
                                           text="↑/↓: Previous/Next | S/Esc: Back to Library",
                                           font=("Helvetica", 10), 
                                           fill="#7f8c8d", 
                                           anchor="center")
            
            # Save progress
            self.save_progress(self.current_epub_path, self.current_page)
            
        except Exception as e:
            print(f"Page display error: {e}")

    def display_page_image(self, soup, item):
        """Display image from page"""
        try:
            images = soup.find_all('img')
            img_found = False
            
            for img_tag in images:
                src = img_tag.get('src', '')
                if not src:
                    continue
                    
                # Try to extract image
                img_data = self.extract_image_from_epub(src)
                
                if img_data:
                    self.display_image_data(img_data)
                    img_found = True
                    break
            
            if not img_found:
                # Try ZIP extraction
                try:
                    with zipfile.ZipFile(self.current_epub_path, 'r') as epub_zip:
                        for file_info in epub_zip.infolist():
                            if file_info.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                img_data = epub_zip.read(file_info.filename)
                                self.display_image_data(img_data)
                                img_found = True
                                break
                except Exception as e:
                    print(f"Error extracting from ZIP: {e}")
            
            if not img_found:
                self.reading_canvas.create_text(240, 400, 
                                               text=f"Page {self.current_page + 1}\n(Image not found)",
                                               font=("Helvetica", 16), 
                                               fill="#ecf0f1", 
                                               anchor="center")
                
        except Exception as e:
            print(f"Image display error: {e}")

    def display_image_data(self, img_data):
        """Display image from binary data"""
        try:
            image = Image.open(io.BytesIO(img_data))
            
            # Target display area (480x800 with margins)
            target_width = 440  # 20px margin each side
            target_height = 720  # 40px top, 40px bottom
            
            # Calculate scaling
            img_width, img_height = image.size
            width_ratio = target_width / img_width
            height_ratio = target_height / img_height
            scale_ratio = min(width_ratio, height_ratio)
            
            # Resize
            new_width = int(img_width * scale_ratio)
            new_height = int(img_height * scale_ratio)
            
            if scale_ratio < 1:
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            self.current_image = photo
            
            # Center on canvas
            x_pos = (480 - new_width) // 2
            y_pos = (800 - new_height) // 2
            
            self.reading_canvas.create_image(x_pos, y_pos, anchor="nw", image=photo)
            
        except Exception as e:
            print(f"Error displaying image: {e}")

    def extract_image_from_epub(self, img_src):
        """Extract image data from EPUB"""
        try:
            img_src = img_src.lstrip('/').replace('../', '')
            
            # Look in book items
            for item in self.current_book.get_items():
                if hasattr(item, 'get_name') and item.get_name():
                    item_name = item.get_name()
                    if img_src in item_name or item_name.endswith(img_src):
                        return item.get_content()
            
            # Check for base64 images
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

    def display_page_text(self, soup):
        """Display text content"""
        # Clean HTML
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if not text:
            text = "(No readable content on this page)"
        
        # Display text with word wrapping
        self.reading_canvas.create_text(240, 100, 
                                       text=text, 
                                       font=("Helvetica", 14), 
                                       fill="#ecf0f1", 
                                       anchor="n",
                                       width=440)

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
        # Save progress
        if self.current_epub_path and self.is_reading:
            self.save_progress(self.current_epub_path, self.current_page)
        
        # Reset state
        self.is_reading = False
        self.current_book = None
        self.spine_items = []
        self.current_page = 0
        self.current_epub_path = None
        self.current_image = None
        
        # Switch frames
        self.reading_frame.pack_forget()
        self.library_frame.pack(fill="both", expand=True)
        
        # Clear error
        self.clear_error()
        
        print("Returned to library")

    # ---------- Key Handling ----------
    def on_key(self, event):
        ch = (event.char or "").upper()
        
        if ch in ("U", "D", "S", "\r"):  # \r is Enter key
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