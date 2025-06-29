#!/usr/bin/env python3
"""
Terminal Script Writer - A minimal TUI for structured screenwriting
Based on David Lynch's 70-card method.
"""

import json
import os
import shutil
import subprocess
import platform
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static, ListView, ListItem, Input, Header, Footer, TextArea, ProgressBar, Button
from textual.screen import Screen
from textual import events
from textual.binding import Binding


# Configuration
CONFIG_DIR = Path.home() / ".scriptwriter"
CONFIG_FILE = CONFIG_DIR / "projects.json"
DEFAULT_SCRIPTS_DIR = Path.home() / "Documents" / "Scripts"


class Project:
    """Manages project data and file operations."""
    
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = Path(path)
        self.cards_dir = self.path / "cards"
        self.exports_dir = self.path / "exports"
        self.order_file = self.path / ".cardorder"
    
    def create(self):
        """Create new project structure."""
        self.path.mkdir(parents=True, exist_ok=True)
        self.cards_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)
        
        # Create default card order
        default_order = list(range(1, 71))
        self.save_card_order(default_order)
        
        # Create empty card files
        for i in range(1, 71):
            card_file = self.cards_dir / f"{i:02d}.md"
            if not card_file.exists():
                card_file.write_text("")
    
    def load_card_order(self) -> List[int]:
        """Load current card order."""
        if self.order_file.exists():
            try:
                order_text = self.order_file.read_text().strip()
                return [int(x) for x in order_text.split(',')]
            except (ValueError, FileNotFoundError):
                pass
        return list(range(1, 71))
    
    def save_card_order(self, order: List[int]):
        """Save card order to file."""
        self.order_file.write_text(','.join(map(str, order)))
    
    def get_card_title_from_file(self, card_num: int) -> str:
        """Get title from markdown file first line."""
        card_file = self.cards_dir / f"{card_num:02d}.md"
        if card_file.exists():
            try:
                content = card_file.read_text()
                if content.strip():
                    first_line = content.split('\n')[0].strip()
                    if first_line.startswith('#'):
                        return first_line[1:].strip()  # Remove # and whitespace
            except:
                pass
        return ""  # Empty title if no file or no header
    
    def load_card_titles(self, progress_callback=None) -> Dict[str, str]:
        """Load titles from all markdown files."""
        titles = {}
        for i in range(1, 71):
            titles[str(i)] = self.get_card_title_from_file(i)
            if progress_callback:
                progress_callback(i, 70)
        return titles
    
    def get_card_content(self, card_num: int) -> str:
        """Get content of a specific card."""
        card_file = self.cards_dir / f"{card_num:02d}.md"
        if card_file.exists():
            return card_file.read_text()
        return ""
    
    def save_card_content(self, card_num: int, content: str):
        """Save content to a specific card."""
        card_file = self.cards_dir / f"{card_num:02d}.md"
        card_file.write_text(content)
    
    def is_card_written(self, card_num: int) -> bool:
        """Check if card has substantial content."""
        content = self.get_card_content(card_num)
        # Consider written if more than just the header
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        return len(lines) > 1 or (len(lines) == 1 and not lines[0].startswith('#'))
    
    def swap_cards(self, pos1: int, pos2: int):
        """Swap two cards in the order."""
        order = self.load_card_order()
        if 0 <= pos1 < len(order) and 0 <= pos2 < len(order):
            order[pos1], order[pos2] = order[pos2], order[pos1]
            self.save_card_order(order)
            return True
        return False
    
    def rename_card(self, card_num: int, new_title: str):
        """Rename a card by updating its markdown header."""
        card_file = self.cards_dir / f"{card_num:02d}.md"
        
        if new_title.strip():
            # Add or update the header
            if card_file.exists():
                content = card_file.read_text()
                lines = content.split('\n')
                
                # If first line is a header, replace it; otherwise prepend
                if lines and lines[0].strip().startswith('#'):
                    lines[0] = f"# {new_title}"
                else:
                    lines.insert(0, f"# {new_title}")
                    if lines[1:] and lines[1].strip():  # Add blank line if content follows
                        lines.insert(1, "")
                
                card_file.write_text('\n'.join(lines))
            else:
                # Create new file with header
                card_file.write_text(f"# {new_title}\n\n")
        else:
            # Remove header if title is empty
            if card_file.exists():
                content = card_file.read_text()
                lines = content.split('\n')
                if lines and lines[0].strip().startswith('#'):
                    lines = lines[1:]
                    # Remove blank line after header if it exists
                    if lines and not lines[0].strip():
                        lines = lines[1:]
                    card_file.write_text('\n'.join(lines))
    
    def export_screenplay_md(self) -> str:
        """Export all cards as a single markdown screenplay."""
        order = self.load_card_order()
        screenplay = f"# {self.name}\n\n"
        screenplay += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        screenplay += "---\n\n"
        
        for i, card_num in enumerate(order, 1):
            content = self.get_card_content(card_num)
            # Remove the title line since we'll use our own
            lines = content.split('\n')[1:]  # Skip first line (title)
            card_content = '\n'.join(lines).strip()
            
            if card_content:
                screenplay += f"## Scene {i}\n\n{card_content}\n\n---\n\n"
        
        return screenplay
    
    def export_fountain(self) -> str:
        """Export as Fountain format."""
        order = self.load_card_order()
        fountain = f"Title: {self.name}\n"
        fountain += f"Author: \n"
        fountain += f"Draft date: {datetime.now().strftime('%m/%d/%Y')}\n\n"
        
        for i, card_num in enumerate(order, 1):
            content = self.get_card_content(card_num)
            lines = content.split('\n')[1:]  # Skip title
            card_content = '\n'.join(lines).strip()
            
            if card_content:
                fountain += f"INT./EXT. SCENE {i}\n\n{card_content}\n\n"
        
        return fountain
    
    def export_outline(self) -> str:
        """Export as simple outline."""
        order = self.load_card_order()
        outline = f"# {self.name} - Story Outline\n\n"
        
        for i, card_num in enumerate(order, 1):
            title = self.get_card_title_from_file(card_num)
            status = "●" if self.is_card_written(card_num) else "○"
            
            if title:
                outline += f"{i:02d}. {status} {title}\n"
            else:
                outline += f"{i:02d}. {status} [Card {card_num}]\n"
        
        return outline


class ProjectManager:
    """Manages project configuration and selection."""
    
    @staticmethod
    def load_config() -> dict:
        """Load projects configuration."""
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text())
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {"projects": {}, "last_project": None}
    
    @staticmethod
    def save_config(config: dict):
        """Save projects configuration."""
        CONFIG_DIR.mkdir(exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(config, indent=2))
    
    @staticmethod
    def add_project(name: str, path: str) -> str:
        """Add new project to config."""
        config = ProjectManager.load_config()
        project_id = name.lower().replace(' ', '-').replace('_', '-')
        
        config["projects"][project_id] = {
            "name": name,
            "path": str(path),
            "last_opened": datetime.now().isoformat()
        }
        config["last_project"] = project_id
        
        ProjectManager.save_config(config)
        return project_id
    
    @staticmethod
    def remove_project(project_id: str):
        """Remove project from config but keep files."""
        config = ProjectManager.load_config()
        
        if project_id in config["projects"]:
            del config["projects"][project_id]
            
            # Update last_project if it was the deleted one
            if config.get("last_project") == project_id:
                remaining_projects = list(config["projects"].keys())
                config["last_project"] = remaining_projects[0] if remaining_projects else None
            
            ProjectManager.save_config(config)
        else:
            raise ValueError(f"Project '{project_id}' not found")
    
    @staticmethod
    def delete_project_permanently(project_id: str):
        """Remove project from config AND delete all files."""
        config = ProjectManager.load_config()
        
        if project_id in config["projects"]:
            project_path = Path(config["projects"][project_id]["path"])
            
            # Delete the project directory if it exists
            if project_path.exists():
                shutil.rmtree(project_path)
            
            # Remove from config
            ProjectManager.remove_project(project_id)
        else:
            raise ValueError(f"Project '{project_id}' not found")
    
    @staticmethod
    def get_projects() -> dict:
        """Get all projects."""
        return ProjectManager.load_config()["projects"]
    
    @staticmethod
    def update_last_opened(project_id: str):
        """Update last opened timestamp."""
        config = ProjectManager.load_config()
        if project_id in config["projects"]:
            config["projects"][project_id]["last_opened"] = datetime.now().isoformat()
            config["last_project"] = project_id
            ProjectManager.save_config(config)


class SaveConfirmDialog(Screen):
    """Save confirmation dialog with three options"""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("left", "focus_previous", "Previous", show=False, priority=True),
        Binding("right", "focus_next", "Next", show=False, priority=True),
    ]
    
    CSS = """
    SaveConfirmDialog {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: 11;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #message {
        height: 5;
        content-align: center middle;
    }
    
    #buttons {
        height: 3;
        layout: horizontal;
        align: center middle;
    }
    
    #buttons Button {
        margin: 0 1;
        min-width: 16;
    }
    """
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Static("You have unsaved changes.\nDo you want to save them?", id="message")
            with Container(id="buttons"):
                yield Button("Save", variant="success", id="save")
                yield Button("Don't Save", variant="warning", id="dont_save")
                yield Button("Cancel", variant="primary", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()
        if event.button.id == "save":
            self.callback("save")
        elif event.button.id == "dont_save":
            self.callback("dont_save")
        else:  # cancel
            self.callback("cancel")
    
    def action_cancel(self):
        """Handle escape key"""
        self.dismiss()
        self.callback("cancel")
    
    def action_focus_next(self):
        """Move focus to next button"""
        self.focus_next()
        
    def action_focus_previous(self):
        """Move focus to previous button"""
        self.focus_previous()
    
    def on_mount(self):
        """Set initial focus to Cancel button"""
        cancel_button = self.query_one("#cancel", Button)
        cancel_button.focus()


class ProjectLoadingScreen(Screen):
    """Screen shown while loading a project with progress."""
    
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.current_progress = 0
        self.total_cards = 70
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(f"📝 Loading '{self.project.name}'...", id="loading_title"),
            Static("", id="loading_status"),
            ProgressBar(total=self.total_cards, id="progress_bar"),
            Static("", id="progress_text"),
            id="loading_container"
        )
        yield Footer()
    
    def on_mount(self):
        """Start loading the project."""
        self.load_project_async()
    
    def update_progress(self, current: int, total: int):
        """Update the progress display."""
        self.current_progress = current
        
        # Update progress bar
        progress_bar = self.query_one("#progress_bar", ProgressBar)
        progress_bar.update(progress=current)
        
        # Update status text
        status = self.query_one("#loading_status", Static)
        status.update(f"Loading cards... {current}/{total}")
        
        # Update progress percentage
        progress_text = self.query_one("#progress_text", Static)
        percentage = (current / total) * 100
        progress_text.update(f"{percentage:.0f}% complete")
    
    def load_project_async(self):
        """Load project data with progress updates."""
        try:
            # Load card titles with progress callback
            self.project.load_card_titles(progress_callback=lambda current, total: self.update_progress(current, total))
            
            # Loading complete
            self.loading_complete()
        except Exception as e:
            self.notify(f"Error loading project: {e}", severity="error")
            self.app.pop_screen()
    
    def loading_complete(self):
        """Called when loading is finished."""
        self.app.switch_screen(EditorScreen(self.project))


class EditorHelpScreen(Screen):
    """Help screen showing all editor commands."""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]
    
    def compose(self) -> ComposeResult:
        help_text = """
# scriptedt - Editor Help

## Text Editing
Normal typing works as expected in the editor.
All shortcuts work while typing using Ctrl combinations.

## File Operations
- **Ctrl+S**: Save card
- **Ctrl+Q**: Quit application
- **Esc**: Close editor (with save dialog if unsaved changes)

## Clipboard Operations
- **Ctrl+Y**: Copy selected text
- **Ctrl+V**: Paste from clipboard
- **Ctrl+X**: Cut selected text

## Text Operations
- **Ctrl+A**: Select all text
- **Ctrl+Z**: Undo last action

## Card Management
Commands to use in main editor:
- **swap A B**: Swap cards at positions A and B
- **rename N "title"**: Give card N a title
- **open N**: Edit card number N

## Navigation
- **E**: Edit selected card (from main view)
- **O**: Show story outline
- **X**: Export menu
- **Esc**: Return to projects

## Export Formats
- **Markdown**: Clean screenplay format
- **Fountain**: Industry standard format
- **Outline**: Story structure overview

---
💡 **Tip**: All shortcuts use Ctrl+key to avoid conflicts with normal typing.
"""
        
        yield Header()
        yield Static(help_text, id="help_content")
        yield Footer()
    
    def action_close(self):
        """Close help screen."""
        self.app.pop_screen()


class ProjectSelectionScreen(Screen):
    """Screen for selecting or creating projects."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("n", "new_project", "New Project"),
        Binding("d", "delete_project", "Delete"),
        Binding("?", "show_help", "Help"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("# scriptedt - Select Project\n", id="title")
        yield ListView(id="project_list")
        yield Footer()
    
    def on_mount(self):
        """Setup project list when screen loads."""
        self.refresh_project_list()
    
    def refresh_project_list(self):
        """Refresh the project list."""
        project_list = self.query_one("#project_list", ListView)
        project_list.clear()
        
        projects = ProjectManager.get_projects()
        
        if not projects:
            project_list.append(ListItem(Static("No projects yet. Press 'N' to create one.")))
        else:
            for project_id, project_data in projects.items():
                name = project_data["name"]
                last_opened = project_data.get("last_opened", "Never")
                if last_opened != "Never":
                    try:
                        dt = datetime.fromisoformat(last_opened)
                        last_opened = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        last_opened = "Unknown"
                
                item_text = f"{name}\n  Last opened: {last_opened}"
                list_item = ListItem(Static(item_text))
                list_item.project_id = project_id
                project_list.append(list_item)
    
    def action_new_project(self):
        """Create new project."""
        self.app.push_screen(NewProjectScreen(), self.on_new_project)
    
    def action_delete_project(self):
        """Delete selected project."""
        project_list = self.query_one("#project_list", ListView)
        if project_list.highlighted_child and hasattr(project_list.highlighted_child, 'project_id'):
            project_id = project_list.highlighted_child.project_id
            projects = ProjectManager.get_projects()
            project_data = projects[project_id]
            self.app.push_screen(DeleteProjectScreen(project_id, project_data), self.on_project_deleted)
        else:
            self.notify("No project selected", severity="warning")
    
    def on_project_deleted(self, result):
        """Handle project deletion result."""
        if result:
            self.refresh_project_list()
    
    def on_new_project(self, result):
        """Handle new project creation result."""
        if result:
            self.refresh_project_list()
    
    def action_quit(self):
        """Quit the application."""
        self.app.exit()
    
    def action_show_help(self):
        """Show general help screen."""
        self.app.push_screen(GeneralHelpScreen())
    
    def on_list_view_selected(self, event):
        """Handle project selection."""
        if hasattr(event.item, 'project_id'):
            projects = ProjectManager.get_projects()
            project_data = projects[event.item.project_id]
            
            # Update last opened
            ProjectManager.update_last_opened(event.item.project_id)
            
            # Create project instance and show loading screen
            project = Project(project_data["name"], project_data["path"])
            self.app.push_screen(ProjectLoadingScreen(project))


class DeleteProjectScreen(Screen):
    """Screen for confirming project deletion with options."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("1", "remove_from_list", "Remove from List"),
        Binding("2", "delete_permanently", "Delete Permanently"),
    ]
    
    def __init__(self, project_id: str, project_data: dict):
        super().__init__()
        self.project_id = project_id
        self.project_data = project_data
    
    def compose(self) -> ComposeResult:
        project_name = self.project_data["name"]
        yield Header()
        yield Vertical(
            Static(f"# Delete Project\n"),
            Static(f"Delete '{project_name}'?\n"),
            Static("[1] Remove from list only"),
            Static("    (Keeps files safe on disk)\n"),
            Static("[2] Delete files permanently"),
            Static("    (⚠️  Removes all project files)\n"),
            Static("[Escape] Cancel"),
            id="delete_form"
        )
        yield Footer()
    
    def action_remove_from_list(self):
        """Remove project from list but keep files."""
        try:
            ProjectManager.remove_project(self.project_id)
            self.notify("Project removed from list (files kept)", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error removing project: {e}", severity="error")
    
    def action_delete_permanently(self):
        """Delete project files permanently."""
        # Show additional confirmation for permanent deletion
        self.app.push_screen(
            ConfirmDeletionScreen(self.project_data["name"]), 
            self.on_confirm_permanent_deletion
        )
    
    def on_confirm_permanent_deletion(self, confirmed):
        """Handle permanent deletion confirmation."""
        if confirmed:
            try:
                ProjectManager.delete_project_permanently(self.project_id)
                self.notify("Project deleted permanently", severity="information")
                self.dismiss(True)
            except Exception as e:
                self.notify(f"Error deleting project: {e}", severity="error")
    
    def action_cancel(self):
        """Cancel deletion."""
        self.dismiss(False)


class ConfirmDeletionScreen(Screen):
    """Final confirmation screen for permanent deletion."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("y", "confirm", "Yes, Delete"),
        Binding("n", "cancel", "No, Cancel"),
    ]
    
    def __init__(self, project_name: str):
        super().__init__()
        self.project_name = project_name
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("# ⚠️  PERMANENT DELETION\n"),
            Static(f"Are you absolutely sure you want to"),
            Static(f"PERMANENTLY DELETE '{self.project_name}'?\n"),
            Static("This action CANNOT be undone!\n"),
            Static("[Y] Yes, delete permanently"),
            Static("[N] No, cancel"),
            id="confirm_form"
        )
        yield Footer()
    
    def action_confirm(self):
        """Confirm permanent deletion."""
        self.dismiss(True)
    
    def action_cancel(self):
        """Cancel permanent deletion."""
        self.dismiss(False)


class NewProjectScreen(Screen):
    """Screen for creating new projects."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+c", "cancel", "Cancel"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("# Create New Project\n"),
            Static("Project Name:"),
            Input(placeholder="My Amazing Script", id="project_name"),
            Static("\nProject Location:"),
            Input(value=str(DEFAULT_SCRIPTS_DIR), id="project_path"),
            id="form"
        )
        yield Footer()
    
    def on_input_submitted(self, event):
        """Handle form submission."""
        name_input = self.query_one("#project_name", Input)
        path_input = self.query_one("#project_path", Input)
        
        name = name_input.value.strip()
        base_path = Path(path_input.value.strip())
        
        if not name:
            self.notify("Please enter a project name", severity="error")
            return
        
        # Create project folder
        project_path = base_path / name.replace(' ', '-')
        
        try:
            project = Project(name, project_path)
            project.create()
            
            # Add to config
            ProjectManager.add_project(name, str(project_path))
            
            self.dismiss(True)
            self.notify(f"Created project: {name}", severity="information")
            
        except Exception as e:
            self.notify(f"Error creating project: {e}", severity="error")
    
    def action_cancel(self):
        """Cancel project creation."""
        self.dismiss(False)


class GeneralHelpScreen(Screen):
    """General help screen for the application."""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]
    
    def compose(self) -> ComposeResult:
        help_text = """
# scriptedt - Help

## David Lynch's 70-Card Method
This app implements a digital version of David Lynch's 17-card screenwriting method, scaled to 70 cards for feature-length scripts.

## Project Management
- **Enter**: Open selected project
- **N**: Create new project
- **D**: Delete selected project (safe options)
- **Q**: Quit application
- **?**: Help

## Card Organization
Each project has 70 numbered cards representing story beats.

### Commands (in main editor):
- **swap 3 5**: Swap cards at positions 3 and 5
- **rename 2 "title"**: Give card 2 a title
- **open 5**: Edit card 5

### Navigation:
- **E**: Edit current card
- **O**: Show story outline
- **X**: Export options
- **Esc**: Return to projects

## Text Editor
Simple editing with Ctrl+key shortcuts that work while typing:
- **Ctrl+S**: Save
- **Ctrl+Q**: Quit application
- **Ctrl+Y**: Copy selected text
- **Ctrl+V**: Paste

Press **?** in any screen for specific help.

## Export Formats
- **Markdown**: Clean screenplay format
- **Fountain**: Industry standard
- **Outline**: Story structure overview

---
💡 **Philosophy**: "Workflow is automation, not creation"
"""
        
        yield Header()
        yield Static(help_text, id="help_content")
        yield Footer()
    
    def action_close(self):
        """Close help screen."""
        self.app.pop_screen()


class EditorScreen(Screen):
    """Main editor screen with card list and preview."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("e", "edit_card", "Edit"),
        Binding("o", "outline", "Outline"),
        Binding("x", "export", "Export"),
        Binding("escape", "back_to_projects", "Projects"),
        Binding("?", "show_help", "Help"),
    ]
    
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.current_card = 1
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Static(f"# {self.project.name}", id="project_title"),
                ListView(id="card_list"),
                id="left_panel"
            ),
            Vertical(
                Static("# Card Preview", id="preview_title"),
                Static("", id="card_preview"),
                id="right_panel"
            )
        )
        yield Input(placeholder="Enter command (swap 3 5, rename 2 'title', etc.)", id="command_input")
        yield Footer()
    
    def on_mount(self):
        """Setup editor when screen loads."""
        self.refresh_card_list()
        self.update_preview()
    
    def refresh_card_list(self):
        """Refresh the card list display."""
        card_list = self.query_one("#card_list", ListView)
        card_list.clear()
        
        order = self.project.load_card_order()
        titles = self.project.load_card_titles()  # Now reads from markdown files
        
        for i, card_num in enumerate(order):
            title = titles.get(str(card_num), "")
            status = "●" if self.project.is_card_written(card_num) else "○"
            
            # Clean display - show title only if it exists and isn't just a number
            if title and title.strip():
                item_text = f"[{card_num:02d}] {status} {title}"
            else:
                item_text = f"[{card_num:02d}] {status}"
            
            list_item = ListItem(Static(item_text))
            list_item.card_num = card_num
            list_item.position = i
            card_list.append(list_item)
    
    def update_preview(self):
        """Update the card preview panel."""
        preview = self.query_one("#card_preview", Static)
        content = self.project.get_card_content(self.current_card)
        
        # Limit preview to first few lines
        lines = content.split('\n')[:10]
        preview_text = '\n'.join(lines)
        if len(content.split('\n')) > 10:
            preview_text += "\n\n[...more content...]"
        
        preview.update(preview_text)
    
    def on_list_view_selected(self, event):
        """Handle card selection."""
        if hasattr(event.item, 'card_num'):
            self.current_card = event.item.card_num
            self.update_preview()
    
    def on_input_submitted(self, event):
        """Handle command input."""
        command = event.value.strip()
        command_input = self.query_one("#command_input", Input)
        command_input.value = ""
        
        if command:
            self.execute_command(command)
    
    def execute_command(self, command: str):
        """Execute user commands."""
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        
        if cmd == "swap" and len(parts) == 3:
            try:
                pos1, pos2 = int(parts[1]) - 1, int(parts[2]) - 1
                if self.project.swap_cards(pos1, pos2):
                    self.refresh_card_list()
                    self.notify(f"Swapped positions {parts[1]} and {parts[2]}")
                else:
                    self.notify("Invalid positions", severity="error")
            except ValueError:
                self.notify("Invalid command format", severity="error")
        
        elif cmd == "rename" and len(parts) >= 3:
            try:
                card_num = int(parts[1])
                new_title = ' '.join(parts[2:]).strip('"\'')
                self.project.rename_card(card_num, new_title)
                self.refresh_card_list()
                self.notify(f"Renamed card {card_num}")
            except ValueError:
                self.notify("Invalid command format", severity="error")
        
        elif cmd == "open" and len(parts) == 2:
            try:
                card_num = int(parts[1])
                self.edit_card(card_num)
            except ValueError:
                self.notify("Invalid card number", severity="error")
        
        else:
            self.notify("Unknown command. Try: swap 3 5, rename 2 'title', open 5", severity="error")
    
    def edit_card(self, card_num: int):
        """Edit a card using built-in text editor."""
        self.app.push_screen(TextEditorScreen(self.project, card_num), self.on_card_edited)
    
    def on_card_edited(self, result=None):
        """Handle return from card editor."""
        # Refresh display after editing
        self.refresh_card_list()
        if hasattr(self, 'current_card'):
            self.update_preview()
    
    def action_edit_card(self):
        """Edit current selected card."""
        self.edit_card(self.current_card)
    
    def action_outline(self):
        """Show outline view."""
        outline = self.project.export_outline()
        self.app.push_screen(TextDisplayScreen("Outline", outline))
    
    def action_export(self):
        """Show export options."""
        self.app.push_screen(ExportScreen(self.project))
    
    def action_back_to_projects(self):
        """Return to project selection."""
        self.app.switch_screen(ProjectSelectionScreen())
    
    def action_show_help(self):
        """Show main editor help."""
        self.app.push_screen(GeneralHelpScreen())


class TextEditorScreen(Screen):
    """Screen for editing card content with built-in text editor."""
    
    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("ctrl+q", "quit_app", "Quit App", priority=True),
        Binding("escape", "close_with_save_check", "Close", priority=True),
        Binding("ctrl+y", "copy_selected", "Copy", priority=True),
        Binding("ctrl+v", "paste", "Paste", priority=True),
        Binding("ctrl+x", "cut", "Cut", priority=True),
        Binding("ctrl+a", "select_all", "Select All", priority=True),
        Binding("ctrl+z", "undo", "Undo", priority=True),
        Binding("?", "show_help", "Help", priority=True),
    ]
    
    def __init__(self, project: Project, card_num: int):
        super().__init__()
        self.project = project
        self.card_num = card_num
        self.original_content = project.get_card_content(card_num)
        self.has_changes = False
    
    def compose(self) -> ComposeResult:
        card_title = self.project.get_card_title_from_file(self.card_num)
        
        # Show card number if no title, or title if it exists
        if card_title:
            header_title = f"# Editing: [{self.card_num:02d}] {card_title}"
        else:
            header_title = f"# Editing: Card [{self.card_num:02d}]"
        
        yield Header()
        yield Static(header_title, id="editor_title")
        yield TextArea(
            text=self.original_content,
            language="markdown",
            id="text_editor"
        )
        yield Footer()
    
    def on_mount(self):
        """Focus the text editor."""
        text_area = self.query_one("#text_editor", TextArea)
        text_area.focus()
    
    def action_show_help(self):
        """Show help screen."""
        self.app.push_screen(EditorHelpScreen())
    
    def on_text_area_changed(self, event):
        """Track changes to the text."""
        self.has_changes = True
    
    def action_save(self):
        """Save the current content."""
        text_area = self.query_one("#text_editor", TextArea)
        content = text_area.text
        self.project.save_card_content(self.card_num, content)
        self.has_changes = False
        self.notify(f"Saved card {self.card_num}")
    
    def action_quit_app(self):
        """Quit the entire application."""
        self.app.exit()
    
    def action_close_with_save_check(self):
        """Close editor with save check dialog."""
        if self.has_changes:
            # Show save dialog with three options
            def handle_save_choice(choice):
                if choice == "save":
                    self.action_save()
                    self.app.pop_screen()
                elif choice == "dont_save":
                    self.app.pop_screen()
                # else: cancel - do nothing
            
            self.app.push_screen(SaveConfirmDialog(handle_save_choice))
        else:
            # No changes, just close
            self.app.pop_screen()
    
    def action_save_and_close(self):
        """Save and close the editor."""
        self.action_save()
        self.app.pop_screen()
    
    def action_copy_selected(self):
        """Copy selected text to clipboard."""
        text_area = self.query_one("#text_editor", TextArea)
        try:
            if hasattr(text_area, 'selected_text') and text_area.selected_text:
                self.copy_to_system_clipboard(text_area.selected_text)
                self.notify("Copied selected text")
            else:
                self.notify("No text selected")
        except Exception as e:
            self.notify(f"Copy failed: {e}", severity="error")
    
    def action_paste(self):
        """Paste from clipboard."""
        try:
            clipboard_content = self.get_from_system_clipboard()
            if clipboard_content:
                text_area = self.query_one("#text_editor", TextArea)
                text_area.insert(clipboard_content)
                self.notify("Pasted from clipboard")
            else:
                self.notify("Clipboard is empty")
        except Exception as e:
            self.notify(f"Paste failed: {e}", severity="error")
    
    def action_cut(self):
        """Cut selected text."""
        text_area = self.query_one("#text_editor", TextArea)
        try:
            if hasattr(text_area, 'selected_text') and text_area.selected_text:
                self.copy_to_system_clipboard(text_area.selected_text)
                text_area.delete_selection()
                self.notify("Cut selected text")
            else:
                self.notify("No text selected")
        except Exception as e:
            self.notify(f"Cut failed: {e}", severity="error")
    
    def action_select_all(self):
        """Select all text."""
        text_area = self.query_one("#text_editor", TextArea)
        text_area.select_all()
    
    def action_undo(self):
        """Undo last action."""
        text_area = self.query_one("#text_editor", TextArea)
        text_area.undo()
    
    def copy_to_system_clipboard(self, text: str):
        """Copy text to system clipboard."""
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
        elif system == "Linux":
            subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
        elif system == "Windows":
            subprocess.run(["clip"], input=text, text=True, check=True)
    
    def get_from_system_clipboard(self) -> str:
        """Get text from system clipboard."""
        system = platform.system()
        if system == "Darwin":  # macOS
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return result.stdout
        elif system == "Linux":
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, check=True)
            return result.stdout
        elif system == "Windows":
            result = subprocess.run(["powershell", "-command", "Get-Clipboard"], capture_output=True, text=True, check=True)
            return result.stdout
        return ""


class TextDisplayScreen(Screen):
    """Screen for displaying text (outline, exports, etc.)."""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]
    
    def __init__(self, title: str, content: str):
        super().__init__()
        self.title = title
        self.content = content
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"# {self.title}\n\n{self.content}", id="content")
        yield Footer()
    
    def action_close(self):
        """Close this screen."""
        self.app.pop_screen()


class ExportScreen(Screen):
    """Screen for export options."""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("1", "export_md", "Markdown"),
        Binding("2", "export_fountain", "Fountain"),
        Binding("3", "export_outline", "Outline"),
    ]
    
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("# Export Options\n")
        yield Static("[1] Screenplay Markdown (.md)")
        yield Static("[2] Fountain Format (.fountain)")
        yield Static("[3] Story Outline (.txt)")
        yield Footer()
    
    def action_export_md(self):
        """Export as markdown."""
        content = self.project.export_screenplay_md()
        filename = f"{self.project.name.replace(' ', '-')}-screenplay.md"
        self.save_export(filename, content, "Markdown screenplay")
    
    def action_export_fountain(self):
        """Export as fountain."""
        content = self.project.export_fountain()
        filename = f"{self.project.name.replace(' ', '-')}.fountain"
        self.save_export(filename, content, "Fountain format")
    
    def action_export_outline(self):
        """Export as outline."""
        content = self.project.export_outline()
        filename = f"{self.project.name.replace(' ', '-')}-outline.txt"
        self.save_export(filename, content, "Story outline")
    
    def save_export(self, filename: str, content: str, format_name: str):
        """Save export to file."""
        try:
            export_file = self.project.exports_dir / filename
            export_file.write_text(content)
            self.notify(f"Exported {format_name} to: {export_file}")
            self.action_close()
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")
    
    def action_close(self):
        """Close export screen."""
        self.app.pop_screen()


class scriptedt(App):
    """Main application."""
    
    CSS = """
    #left_panel {
        width: 20%;
    }
    
    #right_panel {
        width: 80%;
    }
    
    #project_title {
        margin: 1;
    }
    
    #preview_title {
        margin: 1;
    }
    
    #card_preview {
        margin: 1;
        height: 80%;
        overflow: auto;
    }
    
    #command_input {
        margin: 1;
    }
    
    #form {
        margin: 2;
    }
    
    #content {
        margin: 1;
        overflow: auto;
    }
    
    #editor_title {
        margin: 1;
    }
    
    #text_editor {
        margin: 1;
        height: 90%;
    }
    
    #loading_container {
        margin: 4;
        padding: 2;
        text-align: center;
    }
    
    #loading_title {
        margin: 2;
        text-align: center;
        text-style: bold;
    }
    
    #loading_status {
        margin: 1;
        text-align: center;
    }
    
    #progress_bar {
        margin: 2;
        width: 80%;
    }
    
    #progress_text {
        margin: 1;
        text-align: center;
        color: $text-muted;
    }
    
    #delete_form {
        margin: 4;
        padding: 2;
    }
    
    #confirm_form {
        margin: 4;
        padding: 2;
        text-align: center;
    }
    
    #help_content {
        margin: 2;
        padding: 1;
        overflow: auto;
    }
    """
    
    def on_mount(self):
        """Initialize the app."""
        self.push_screen(ProjectSelectionScreen())


if __name__ == "__main__":
    app = scriptedt()
    app.run()