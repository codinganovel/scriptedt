# scriptedt
**scriptedt** is a minimalist, card-based screenplay editor for your terminal. It helps you outline, draft, and export scripts with David Lynch’s expanded **70-card** method, all inside a snappy Textual UI.

> Structure your story, one card at a time.

---

## ✨ Features
- 70 numbered cards per project, mirroring feature-length story beats  
- Split-pane TUI with live preview and command line  
- Intuitive commands (`swap`, `rename`, `open`) and single-key navigation (`E / O / X / ?`)  
- Built-in Markdown editor with familiar **Ctrl** shortcuts  
- One-keystroke export to **Markdown screenplay**, **Fountain**, or **plain-text outline**  
- Automatic per-card Markdown files 
- Cross-platform clipboard integration (macOS / Linux / Windows)  

---

## 📦 Installation

[get yanked](https://github.com/codinganovel/yanked)

---

### Available Commands
| Command / Shortcut   | Description                                    |
|----------------------|------------------------------------------------|
| `swap A B`           | Swap cards at positions **A** and **B**        |
| `rename N "title"`   | Give card **N** a title                        |
| `open N`             | Open card **N** in the editor                  |
| `E`                  | Edit highlighted card                          |
| `O`                  | Display story outline                          |
| `X`                  | Export menu                                    |
| `Ctrl+S`             | Save current card                              |
| `Ctrl+Q`             | Quit application                               |
| `?`                  | Context-sensitive help                         |

A project folder (with `cards/` and `exports/` directories) is created automatically on first save.

---

## 📋 Clipboard Support & Dependencies
`scriptedt` talks to your system clipboard directly—no extra Python packages needed.

### macOS  
✅ Uses built-in `pbcopy / pbpaste`  

### Windows  
✅ Works via `clip` / PowerShell  

### Linux  
⚠️ Install a clipboard helper first:
```bash
sudo apt install xclip   # or
sudo apt install xsel
```

---

## 🚚 Export Formats
- `Screenplay.md` – clean, print-ready Markdown screenplay  
- `Title.fountain` – industry-standard Fountain file  
- `Title-outline.txt` – single-page story outline  

---

## 📄 License

under ☕️, check out [the-coffee-license](https://github.com/codinganovel/The-Coffee-License)

I've included both licenses with the repo, do what you know is right. The licensing works by assuming you're operating under good faith.

---

## ✍️ Created by Sam  
Because every great screenplay starts with a blank card.
