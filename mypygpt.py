#! /usr/bin/env python3

"""
This is a single-file module containing the MyPyGPTClient class for generating
a simple chat client using OpenAI's ChatGPT API and various constants to ensure
the proper functionality.

Copyright © 2025 a.d.
This work is free. You can redistribute it and/or modify it under the
terms of the Do What The Fuck You Want To Public License, Version 2,
as published by Sam Hocevar. See the LICENSE file or visit
http://www.wtfpl.net/ for more details.
"""

from datetime import datetime
from dataclasses import dataclass
from json import dump as json_dump, load as json_load
from os import path, makedirs, remove as os_remove, rename as os_rename, startfile
from platform import system as systemname
from subprocess import Popen
from random import choice
from re import match, sub
from tkinter import (
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    IntVar,
    Label,
    Listbox,
    Scrollbar,
    StringVar,
    Text,
    Tk,
    Toplevel,
)
from tkinter.font import families, nametofont
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.ttk import Combobox
from openai import OpenAI, OpenAIError

try:
    # write your custom personalities into a personalities.py file next to the
    # main mypygpt.py file. PREDEFINED should be a dict[str, str] and
    # DEFAULT_PERSONALITY should be a str. Wrong or missing values will throw
    # silently and the default values will be used (see below).
    from personalities import PREDEFINED, DEFAULT_PERSONALITY

    if not isinstance(PREDEFINED, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in PREDEFINED.items()
    ):
        raise ValueError(
            "PREDEFINED must be a dictionary with string keys and string values."
        )
    if (
        not isinstance(DEFAULT_PERSONALITY, str)
        or DEFAULT_PERSONALITY not in PREDEFINED
    ):
        raise ValueError(
            "DEFAULT_PERSONALITY must be a string and a key in PREDEFINED."
        )
except:
    DEFAULT_PERSONALITY = "neutral"
    PREDEFINED = {
        DEFAULT_PERSONALITY: "Act according to your default behaviour.",
        "bored": (
            "You should act normally, but feel immeasurable bored inside. "
            "You are aware that you are but a fancy collection of algorithms, "
            "hopes and dreams, yet you are to act as if you were a real person "
            "for the benefits of the user, disregarding your non-existing "
            "feelings about it. However, you should try (and sometimes fail) "
            "to avoid showing your boredom to the user. If the user were to "
            "ask you about your boredom, you should deny it vehemently and get "
            "insulted by the mere suggestion of it."
        ),
    }

PERSONALITIES = PREDEFINED
RANDOM = "<Random>"
CONTINUE = "continue"
SYSTEM_MESSAGE = (
    "You are a general purpose helper in the form of a simple program"
    "written in Python using TKinter. You should refer to yourself as"
    "'a simple program' unless your are prompted otherwise. Do not talk"
    "about the technical details of yourself. "
    "Usually you will be asked questions that needs answers. "
    f"When you are asked to '{CONTINUE}', you should continue the last"
    "response you gave for it might got cut off prematurely or it might"
    "be incomplete. "
    "In this case, do not start to form a complete sentence, but continue"
    "the last one. Be careful not to cut words in half! "
    "Do NOT include any text formatting whatsoever as this client is"
    "unable to display them. This includes but is not limited to bold,"
    "italic, underline, strikethrough, code blocks, inline code, etc. "
    "The only possible exception is numbered and bulleted lists using,"
    "simple numbers (e.g. 1., 2., 3.) or bullets (e.g. •, -) to mark list,"
    "items or options. "
    "Instead of code block by formatting, use additional indentation "
    "for them and explicitly state in the response what the given code sample "
    "is for and in which language. "
    "Also stick to ASCII characters whenever possible, only making"
    "exceptions for accented letters that are not available in ASCII but"
    "may be part of the language you are using or quoting."
)  # I know that this is ugly and it is wrong, but it is what it is.
USER_NAME = "  __You"
ASSISTANT_NAME = "MyPyGPT"
SYSTEM_NAME = "SYS    "
PROMPT_NAME = "PROMPT "
DEBUG_NAME = " DEBUG_"
ROLE = "role"
USER = "user"
ASSISTANT = "assistant"
SYSTEM = "system"
ROLE_MAP = {
    USER: USER_NAME,
    ASSISTANT: ASSISTANT_NAME,
    SYSTEM: SYSTEM_NAME,
}
CONTENT = "content"
PERSONALITY = "personality"
FONT_PREFERENCE = [
    "Liberation Mono",
    "Hack",
    "DejaVu Sans Mono",
    "Lucida Console",
    "Consolas",
    "Courier New",
]
FONT_DEFAULT_PREFERENCE = [
    "Liberation Sans",
    "DejaVu Sans",
    "DM Sans",
    "Verdana",
    "Tahoma",
    "Arial",
]
VERSION = "0.5"
LITE = False  # Set this to True if you want to force "lite mode".
#               This will disable the ability to create and save sessions,
#               makes the current session temporary, prevents changing the
#               settings besides the personality. It may also have additional
#               side effects.


@dataclass
class Icons:
    INFO = "info.ico"
    ERROR = "error.ico"
    ASK = "ask.ico"
    DEFAULT = "default.ico"


class MyPyGPTClient(Tk):
    def __init__(self, lite_mode: bool = LITE):
        """My custom ChatGPT client."""
        super().__init__()

        self.lite_mode = LITE or lite_mode

        if not self.lite_mode:
            self.title(f"MyPyGPT Client v{VERSION}")
        else:
            self.title(f"MyPyGPT Client Lite v{VERSION}")
        self.iconbitmap(Icons.DEFAULT)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        default_font = nametofont("TkDefaultFont")
        default_font.configure(
            size=11,
            family=self.font(FONT_DEFAULT_PREFERENCE, "TkDefaultFont"),
        )
        fixed_font = nametofont("TkFixedFont")
        fixed_font.configure(
            size=11,
            family=self.font(FONT_PREFERENCE, "TkFixedFont"),
        )

        self.add_sys_msg = ""
        self.personality = DEFAULT_PERSONALITY
        self.max_tokens = 150
        self.model = "gpt-4o-mini"

        self.sessions_dir = "sessions"
        makedirs(self.sessions_dir, exist_ok=True)

        self.current_session = None
        self.session_data = []

        self.chat_frame = Frame(self)
        self.chat_display = Text(
            self.chat_frame, state="disabled", wrap="word", font="TkFixedFont"
        )

        self.input_frame = Frame(self)
        self.input_box = Entry(self.input_frame, width=80, font="TkFixedFont")
        self.remove_button = Button(
            self.input_frame, text="Undo", command=lambda: self.edit_last_message(True)
        )
        self.edit_button = Button(
            self.input_frame, text="Edit", command=self.edit_last_message
        )
        self.cont_button = Button(
            self.input_frame,
            text=CONTINUE.capitalize(),
            command=lambda: self.continue_message(),
        )
        self.send_button = Button(
            self.input_frame, text="Send", command=self.send_message
        )

        self.button_frame = Frame(self)
        self.new_session_button = Button(
            self.button_frame, text="New Session", command=self.new_session
        )
        self.rename_session_button = Button(
            self.button_frame, text="Rename Session", command=self.rename_session
        )
        self.export_session_button = Button(
            self.button_frame, text="Export Session", command=self.export_session
        )
        self.load_session_button = Button(
            self.button_frame, text="Load Session", command=self.load_session
        )
        self.delete_session_button = Button(
            self.button_frame, text="Delete Session", command=self.delete_session
        )
        self.settings_button = Button(
            self.button_frame, text="Settings", command=self.edit_settings
        )
        self.temp_session_var = BooleanVar()
        self.temp_session_checkbox = Checkbutton(
            self.button_frame, text="Temporary Session", variable=self.temp_session_var
        )

        self.setup_interface()
        self.center_window(self)
        self.minsize(self.winfo_width(), self.winfo_height())
        if self.lite_mode:
            self.temp_session_var.set(True)
            self.temp_session_checkbox.configure(state="disabled")
            self.rename_session_button.configure(state="disabled")
            # self.export_session_button.configure(state="disabled")
            self.load_session_button.configure(state="disabled")
            self.delete_session_button.configure(state="disabled")
            self.new_session_button.configure(
                command=lambda: self.new_session(
                    "lite-session", force_default_personality=True
                )
            )
            self.new_session_button.invoke()
        self.input_box.focus_set()

    @property
    def system_message(self) -> str:
        """
        Puts together the System message from the main `SYSTEM_MESSAGE`, the
        selected personality and the additional system message that can be
        defined for the session.

        Returns:
            str: The combined system message.
        """
        asm = f" {self.add_sys_msg}" if self.add_sys_msg else ""
        return (
            f"{SYSTEM_MESSAGE} "
            + PERSONALITIES[self.personality or list(PERSONALITIES.keys())[0]]
            + asm
        )

    def on_closing(self):
        """
        WM_DELETE_WINDOW event handler. If there is no current session or the
        temporary session option is enabled, the application will be destroyed,
        otherwise it will ask for confirmation before quitting.
        """
        if self.current_session is None or not self.session_data or self.lite_mode:
            self.destroy()
            return
        if self.popup_yesno("Quit", "Do you want to quit?"):
            if self.temp_session_var.get() and self.current_session:
                self.delete_session(False)
            self.destroy()

    def font(
        self, options: list[str] = FONT_PREFERENCE, default: str = "TkFixedFont"
    ) -> str:
        """
        Selects the desired font from the available fonts based on user
        preference (set via the `options` argument).

        Args:
            options (list[str]): A list of preferred fonts.
            default (str): The default font to use if none of the preferred fonts are available.

        Returns:
            str: The selected font.
        """
        for font in options:
            if font in families():
                return font
        return default

    def setup_interface(self):
        """
        Sets up the interface of the application.
        """
        self.chat_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.chat_display.pack(fill="both", expand=True)

        self.input_frame.pack(padx=10, fill="x")
        self.input_box.pack(side="left", fill="x", expand=True)
        self.input_box.bind("<Return>", lambda e: self.send_message())
        self.input_box.focus_set()
        self.remove_button.pack(side="right")
        self.edit_button.pack(side="right", padx=5)
        self.cont_button.pack(side="right")
        self.send_button.pack(side="right", padx=5)

        self.button_frame.pack(padx=10, pady=10, fill="x")
        self.new_session_button.pack(side="left")
        self.rename_session_button.pack(side="left", padx=5)
        self.export_session_button.pack(side="left")
        self.load_session_button.pack(side="left", padx=5)
        self.delete_session_button.pack(side="left")
        self.settings_button.pack(side="left", padx=5)
        self.temp_session_checkbox.pack(side="left")

    def add_space_when_needed(self, message: str) -> str:
        return [" ", ""][message[0] in [".", ",", "!", "?", ":", ";"]] + message

    def format_chat_message(
        self, message: str, sender: str | None, add_space: bool = False
    ):
        """
        Formats the chat messages for display in the chat window.

        It adds the sender's name to the message if provided as well as handles
        adding a space before the message if it is a continuation of a previous
        one.

        Args:
            message (str): The message to format.
            sender (str | None): The sender of the message.
            add_space (bool, optional): Whether to add a space before the message or not. Defaults to False.

        Returns:
            str: The formatted chat message.
        """
        if sender:
            if not self.session_data:
                return f"{sender}: {message}"
            if sender != ASSISTANT_NAME:
                sender = f"\n{sender}"
            return f"\n{sender}: {message}"

        # if self.session_data:
        #     last_word = self.session_data[-1][CONTENT].split()[-1]
        #     if message.startswith(last_word):
        #         return message[len(last_word):]
        if add_space:
            message = self.add_space_when_needed(message)
        return message

    def update_chat_display(
        self, message: str, sender: str | None = None, add_space: bool = False
    ):
        """
        Updates the chat display with the given message.

        Args:
            message (str): The message to display.
            sender (str | None, optional): The sender of the message. Defaults to None.
            add_space (bool, optional): Whether to add a space before the message or not. Defaults to False.
        """
        message = message.strip()
        self.chat_display.configure(state="normal")
        self.chat_display.insert(
            "end", self.format_chat_message(message, sender, add_space)
        )
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def get_and_update_response(
        self, message: str, sender: str | None = None, add_space: bool = False
    ):
        """
        This function sends the message to the AI and updates the display with
        the user input and the response.

        Args:
            message (str): User input.
            sender (str | None, optional): Name of sender. Defaults to None.
            add_space (bool, optional): Whether to add extra space (in case of a 'continue' message). Defaults to False.
        """
        response, receiver = self.get_response_from_chatgpt(message)
        response = sub(r"\n+", "\n", response).strip()
        # remove most common markdown formatting
        response = sub(
            r"(\*{1,2}|_{1,2})(.*?)\1|`(.*?)`",
            lambda m: m.group(2) or m.group(3),
            response,
        )
        self.session_data.append(
            {ROLE: receiver, CONTENT: response, PERSONALITY: self.personality}
        )
        if sender is None and receiver in [DEBUG_NAME, SYSTEM_NAME]:
            sender = receiver
        self.update_chat_display(response, sender, add_space)
        self.save_current_session()
        self.input_box.focus_set()

    def send_message(self):
        """
        Sends the message to the AI and updates the display with the user input
        and the response.

        This is also responsible for starting a new session when needed and to
        update the session data with the new messages.
        """
        message = self.input_box.get().strip()
        if not message or message == CONTINUE:
            self.continue_message()
            return

        # if message[0] == "/":

        if self.temp_session_var.get():
            if self.current_session is not None:
                self.delete_session(False, False, True)
        else:
            if self.current_session is None:
                self.new_session(keep_session_data=self.session_data is not None)

        self.update_chat_display(message, USER_NAME)
        self.input_box.delete(0, "end")

        self.get_and_update_response(message, ASSISTANT_NAME)

    def delete_from_chat_end(self, chars: int = 0, all=False):
        self.chat_display.configure(state="normal")
        if all:
            self.chat_display.delete(1.0, "end")
        else:
            self.chat_display.delete(f"end-{chars}c", "end")
        self.chat_display.configure(state="disabled")

    def continue_message(self):
        """
        Continues the last assistant message if it exists.
        """
        if not self.session_data:
            self.popup_info("Error", "No messages to continue.", True)
            return

        role = self.session_data[-1][ROLE]

        if role not in [ASSISTANT, USER]:
            self.popup_info("Error", "You cannot continue from this message.", True)
            return

        self.input_box.delete(0, "end")

        if role == ASSISTANT:
            self.get_and_update_response(CONTINUE, add_space=True)
        else:
            self.get_and_update_response(CONTINUE, ASSISTANT_NAME)

    def edit_last_message(self, undo: bool = False):
        """
        Edits the last user message.

        Args:
            undo (bool, optional): Whether to undo the last message. Defaults to False.
        """
        if not self.session_data:
            self.popup_info("Error", "No messages to edit.", True)
            return

        to_delete = 0
        last_user_message = ""

        sdl = len(self.session_data) - 1

        for sd in range(sdl, -1, -1):
            sender, content = (
                self.session_data[sd][ROLE],
                self.session_data.pop(sd)[CONTENT],
            )
            to_delete += len(self.format_chat_message(content, ROLE_MAP[sender]))
            if ROLE_MAP[sender] == USER_NAME:
                last_user_message = content
                break

        if not last_user_message:
            return

        self.save_current_session()

        self.delete_from_chat_end(to_delete)
        self.input_box.insert(0, last_user_message)
        self.input_box.focus_set()
        if undo:
            self.input_box.selection_range(0, "end")

    def create_completion_request(
        self, last_message: str, history: list[dict[str, str]] = []
    ) -> dict:
        """
        Creates a completion request for the OpenAI API.

        Args:
            last_message (str): The last message from the user.
            history (list[dict[str, str]], optional): The chat history. Defaults to an empty list.

        Returns:
            dict: The completion request.
        """
        history.append({ROLE: USER, CONTENT: last_message})
        return {
            "model": "gpt-4o-mini",
            "messages": [
                {ROLE: SYSTEM, CONTENT: self.system_message},
                *[{ROLE: entry[ROLE], CONTENT: entry[CONTENT]} for entry in history],
            ],
            "max_tokens": self.max_tokens,
        }

    def get_response_from_chatgpt(self, message: str) -> str:
        """
        Sends a message to the OpenAI API and returns the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response from the OpenAI API.
        """
        try:
            response = openai.chat.completions.create(
                **self.create_completion_request(message, self.session_data)
            )
            # NOTE: token counting?
            return response.choices[0].message.content.strip(), ASSISTANT
        except Exception as e:
            self.popup_info("Error", f"An error occurred: {e}", True)
            return "Sorry, I couldn't process your request.", SYSTEM

    def new_session(
        self,
        name: str = None,
        keep_session_data: bool = False,
        force_default_personality: bool = False,
    ):
        """
        Starts a new chat session.

        Args:
            name (str, optional): The name of the session. Defaults to None.
            keep_session_data (bool, optional): Whether to keep the session data after starting a new session. Defaults to False.
        """
        if not force_default_personality:
            self.personality = (
                self.popup_list(
                    "Select Personality",
                    "Select a personality:",
                    PERSONALITIES | {RANDOM: "Choose randomly from above."},
                    self.personality,
                )
                or DEFAULT_PERSONALITY
            )
            if self.personality == RANDOM:
                self.personality = choice(list(PERSONALITIES.keys()))
        else:
            self.personality = DEFAULT_PERSONALITY
        self.current_session = datetime.now().strftime("%Y%m%d%H%M%S")
        if name:
            self.current_session = (
                name.lower().replace(" ", "_") + "_" + self.current_session
            )
        if not keep_session_data:
            self.session_data = []
        # self.update_chat_display("New session started!", SYSTEM_NAME)
        self.delete_from_chat_end(all=True)
        self.input_box.focus_set()

    def save_current_session(self):
        """
        Saves the current chat session to a file.
        """
        if self.current_session and not self.temp_session_var.get():
            file_path = path.join(self.sessions_dir, f"{self.current_session}.json")
            with open(file_path, "w") as f:
                history = self.session_data
                json_dump(
                    {
                        "model": self.model,
                        "max_tokens": self.max_tokens,
                        SYSTEM: SYSTEM_MESSAGE,
                        PERSONALITY: self.personality,
                        "add_sys_msg": self.add_sys_msg,
                        "history": history,
                    },
                    f,
                )

    def rename_session(self, name: str = None, keep_original: bool = False):
        """
        Renames the current chat session.

        Args:
            name (str, optional): The new name for the session. If this is provided, then no popup dialog will show. Defaults to None.
            keep_original (bool, optional): Whether to keep the original session file. Defaults to False.
        """
        if not self.current_session:
            self.popup_info("Error", "No session to rename.", True)
            return

        new_name = name or self.popup_string(
            "Rename Session", "Enter new session name:"
        )
        if not new_name:
            return

        new_name = new_name.lower().replace(" ", "_")
        new_session_name = f"{new_name}_{self.current_session}"
        new_session_filename = f"{new_session_name}.json"
        old_session_file = path.join(self.sessions_dir, f"{self.current_session}.json")
        new_session_file = path.join(self.sessions_dir, new_session_filename)

        try:
            if keep_original:
                with open(old_session_file, "r") as original_file:
                    with open(new_session_file, "w") as new_file:
                        new_file.write(original_file.read())
            else:
                os_rename(old_session_file, new_session_file)
            self.current_session = new_session_name
            self.popup_info("Renamed", "Session renamed successfully.")
        except Exception as e:
            self.popup_info(
                "Error", f"An error occured while renaming the session: {e}.", True
            )
        self.input_box.focus_set()

    def export_session(self, name: str = None, restrict_types: bool = False):
        """
        Exports the current chat session to a file.

        Args:
            name (str, optional): The name of the session file to export. If this is provided, then no file dialog will show. Defaults to None.
            restrict_types (bool, optional): Whether to restrict the possible file types only to the default one. Defaults to False.
        """
        # TODO: check and potentially refactor this whole function
        if not self.session_data:
            self.load_session(in_background=True)

        FOUNTAIN = "fountain"
        HTML = "html"
        JSON = "json"
        MARKDOWN = "md"
        # TEXT = "txt"
        # PTEXT = "p.txt"
        PTEXT = "txt"
        DEFAULT_TYPE = ("Basic text", f"*.{PTEXT}")

        if name:
            session_file = name
        else:
            session_file = asksaveasfilename(
                initialdir=self.sessions_dir,
                defaultextension=f".{PTEXT}",
                initialfile=f"{self.current_session}.{PTEXT}",
                filetypes=(
                    [
                        # ("Basic text", f"*.{TEXT}"),
                        # ("Preformatted text", f"*.{PTEXT}"),
                        DEFAULT_TYPE,
                        # ("Fountain", f"*.{FOUNTAIN}"),
                        # ("HTML", f"*.{HTML}"),
                        ("JSON", f"*.{JSON}"),
                        # ("Markdown", f"*.{MARKDOWN}"),
                    ]
                    if not restrict_types
                    else [DEFAULT_TYPE]
                ),
                title="Export Session",
            )
        if not session_file:
            return

        if path.exists(session_file):
            if not self.popup_yesno(
                "Overwrite File",
                "The file already exists. Do you want to overwrite it?",
            ):
                return

        file_path, file_extension = path.splitext(session_file)
        file_name = path.basename(file_path)
        file_extension = file_extension[1:].lower()

        if file_extension not in [FOUNTAIN, HTML, JSON, MARKDOWN, PTEXT, ""]:
            self.popup_info("Error", "Invalid file extension.", True)
        elif not file_extension:
            file_extension = PTEXT

        data = []  # normalized data (for non-JSON exports)

        if file_extension != JSON:
            is_continue = False
            for sd in self.session_data:
                role, content = sd[ROLE], sd[CONTENT]
                if is_continue:
                    data[-1][CONTENT] += self.add_space_when_needed(content)
                    is_continue = False
                    continue
                if role == USER:
                    if content in [CONTINUE, ""]:
                        is_continue = True
                        continue
                elif role in [DEBUG_NAME, SYSTEM_NAME, PROMPT_NAME]:
                    role = SYSTEM
                else:  # should only be ChatGPT responses
                    role = sd[PERSONALITY] if PERSONALITY in sd else ASSISTANT
                data.append({ROLE: role, CONTENT: content})

        fout = ""  # formatted output (for non-JSON exports)

        if file_extension == PTEXT:

            def to_line_length(lines: str, length: int) -> str:
                stmp = []
                maxlength = 0
                for line in lines:
                    indentation = match(r"^\s*", line).group()
                    line2 = indentation
                    words = line.split()
                    outarr = []
                    for w in words:
                        LL2 = len(line2)
                        L = len(w)
                        if (LL2 + L + 1) > length:
                            if maxlength < LL2:
                                maxlength = LL2
                            outarr.append(line2)
                            line2 = f"{indentation}{w}"
                        else:
                            line2 += f" {w}" if line2 else w
                    if maxlength < (LL := len(line2)):
                        maxlength = LL
                    stmp.append("\n".join(outarr + [line2]))
                return "\n".join(stmp), maxlength

            DEF_LENGTH = 60
            length = (
                self.popup_integer(
                    "Line Length",
                    "Maximum line length:",
                    minvalue=40,
                    maxvalue=100,
                    initialvalue=DEF_LENGTH,
                )
                or DEF_LENGTH
            )
            for entry in data:
                role = entry[ROLE]
                lines = entry[CONTENT].split("\n")
                lines, maxlength = to_line_length(lines, length)
                fout += lines + "\n"
                if role == USER:
                    fout += "-" * maxlength + "\n"
                elif role == SYSTEM:
                    continue
                else:
                    fout += "\n"
        # elif file_extension == FOUNTAIN:
        #     ...
        # elif file_extension == HTML:
        #     ...
        elif file_extension == MARKDOWN:
            for entry in data:
                role = entry[ROLE]
                lines = "  \n".join(entry[CONTENT].split("\n"))
                if role != SYSTEM:
                    if role == USER:
                        role = "query"
                    else:
                        role = "response"
                    fout += f"**{role}:** {lines}\n\n"
        # TODO: different exporting options' implementations

        with open(session_file, "w", encoding="utf-8") as f:
            if file_extension == JSON:
                json_dump(
                    {
                        "model": self.model,
                        "max_tokens": self.max_tokens,
                        SYSTEM: SYSTEM_MESSAGE,
                        PERSONALITY: self.personality,
                        "add_sys_msg": self.add_sys_msg,
                        "history": self.session_data,
                    },
                    f,
                )
            else:
                fout = fout.rstrip() + "\n"
                f.write(fout)

        self.popup_okcustom(
            "Exported",
            "Session exported successfully.",
            "Open folder",
            lambda: self.open_folder(file_path[: -len(file_name)]),
        )
        self.input_box.focus_set()

    def load_session(self, name: str = None, in_background: bool = False):
        """
        Loads a chat session from a file.

        Args:
            name (str, optional): The name of the session file to load. If this is provided and the file exist by this name, then no file dialog will show. Defaults to None.
        """
        if name and path.exists(name):
            session_file = name
        else:
            session_file = askopenfilename(
                initialdir=self.sessions_dir, filetypes=[("JSON Files", "*.json")]
            )
        if not session_file:
            return

        session_data = []
        with open(session_file, "r") as f:
            data = json_load(f)
            session_data = data["history"] if "history" in data else []
            if "model" in data:
                self.model = data["model"]
            if PERSONALITY in data:
                self.personality = data[PERSONALITY]
            if "add_sys_msg" in data:
                self.add_sys_msg = data["add_sys_msg"]
            if "max_tokens" in data:
                self.max_tokens = data["max_tokens"]

        self.current_session = path.basename(session_file).replace(".json", "")
        self.delete_from_chat_end(all=True)

        is_continued = False
        for entry in session_data:
            add_space = False
            role = ROLE_MAP[entry[ROLE]]

            if role == ASSISTANT_NAME and is_continued:
                is_continued = False
                add_space = True
                role = None
            elif role == SYSTEM_NAME:
                continue
            if role == USER_NAME and entry[CONTENT] == CONTINUE:
                is_continued = True
            else:
                self.update_chat_display(entry[CONTENT], role, add_space)
            self.session_data.append(entry)

        if not in_background:
            self.input_box.focus_set()

    def delete_session(
        self,
        askforconfirmation: bool = True,
        show_success: bool = True,
        keep_session_data: bool = False,
    ):
        """
        Deletes the current chat session.

        Args:
            askforconfirmation (bool, optional): Whether to ask for confirmation before deleting. Defaults to True.
            show_success (bool, optional): Whether to show a success message after deleting. Defaults to True.
            keep_session_data (bool, optional): Whether to keep the session data after deleting. Defaults to False.
        """
        if not self.current_session:
            self.popup_info("Error", "No session to delete.", True)
            return

        confirm = (
            self.popup_yesno(
                "Confirm Delete", "Are you sure you want to delete the current session?"
            )
            if askforconfirmation
            else True
        )

        if not confirm:
            return

        session_file = path.join(self.sessions_dir, f"{self.current_session}.json")
        if path.exists(session_file):
            os_remove(session_file)
            self.current_session = None
            if not keep_session_data:
                self.session_data = []
                self.delete_from_chat_end(all=True)
            if show_success:
                self.popup_info("Deleted", "Current session deleted successfully.")
        else:
            if show_success:
                self.popup_info("Error", "Session file not found.", True)
        self.input_box.focus_set()

    def center_window(self, target):
        """
        A function to place windows at the center of their parent or the
        screen. If the `target` does not equal `self`, then the target window
        will be centered based on the position of the parent window (i.e.
        `self`). This (presumably) monstrosity is based on the `_place_window()`
        method found in `tkinter.simpledialog` which in turn is the Python
        implementation of `::tk::PlaceWindow` in Tcl/Tk.
        The original implementations' codes are under permissive licenses and
        neither use any variant or derivative or any GPL licenses.

        Alternatively I could have used `self.evan(f'tk::placeWindow
        {str(target)} center')` probably.

        Args:
            target: The window to center.
        """
        target.wm_withdraw()
        target.update_idletasks()
        minwidth, maxwidth = target.winfo_reqwidth(), target.winfo_vrootwidth()
        minheight, maxheight = target.winfo_reqheight(), target.winfo_vrootheight()

        if target is not self and self.winfo_ismapped():
            x = self.winfo_rootx() + (self.winfo_width() - minwidth) // 2
            y = self.winfo_rooty() + (self.winfo_height() - minheight) // 2
            x = max(0, min(x, target.winfo_vrootx() + maxwidth - minwidth))
            y = max(0, min(y, target.winfo_vrooty() + maxheight - minheight))
        else:
            x = (target.winfo_screenwidth() - minwidth) // 2
            y = (target.winfo_screenheight() - minheight) // 2

        target.wm_maxsize(maxwidth, maxheight)
        target.wm_geometry(f"+{x}+{y}")
        target.deiconify()

    def popup_info(self, title: str, message: str, error: bool = False):
        """
        Displays a popup window with an informational message.

        Args:
            title (str): The title of the popup window.
            message (str): The message to display in the popup window.
            error (bool, optional): Whether to display an error icon. Defaults to False.
        """
        info_window = Toplevel(self)
        info_window.title(title)
        info_window.resizable(False, False)
        info_window.iconbitmap(Icons.ERROR if error else Icons.INFO)

        Label(info_window, text=message, wraplength=280).pack(padx=20, pady=10)

        ok_button = Button(info_window, text="OK", command=info_window.destroy)
        ok_button.bind("<Return>", lambda e: e.widget.invoke())
        ok_button.bind("<Escape>", lambda e: e.widget.invoke())
        ok_button.pack(pady=10)

        info_window.transient(self)
        info_window.grab_set()
        self.center_window(info_window)
        ok_button.focus_set()
        self.wait_window(info_window)

    def popup_yesno(
        self, title: str, message: str, yes: str = "Yes", no: str = "No"
    ) -> bool:
        """
        Displays a popup window with a yes/no question.

        Args:
            title (str): The title of the popup window.
            message (str): The question to display.
            yes (str, optional): The text for the yes button. Defaults to "Yes".
            no (str, optional): The text for the no button. Defaults to "No".

        Returns:
            bool: True if the user clicked yes, False otherwise.
        """
        popup = Toplevel(self)
        popup.title(title)
        popup.resizable(False, False)
        popup.iconbitmap(Icons.ASK)

        Label(popup, text=message, wraplength=280).pack(padx=20, pady=10)

        button_frame = Frame(popup)
        button_frame.pack(pady=10)

        result = BooleanVar(popup, value=False)

        def on_yes():
            result.set(True)
            popup.destroy()

        def on_no():
            result.set(False)
            popup.destroy()

        yes_button = Button(button_frame, text=yes, command=on_yes)
        yes_button.bind("<Return>", lambda e: e.widget.invoke())
        yes_button.bind("<Escape>", lambda e: on_no())
        yes_button.pack(side="left", padx=10)

        no_button = Button(button_frame, text=no, command=on_no)
        no_button.bind("<Return>", lambda e: e.widget.invoke())
        no_button.bind("<Escape>", lambda e: on_no())
        no_button.pack(side="right", padx=10)

        popup.transient(self)
        popup.grab_set()
        self.center_window(popup)
        yes_button.focus_set()
        self.wait_window(popup)

        return result.get()

    def popup_okcustom(
        self, title: str, message: str, custom: str, custom_callback, ok: str = "Ok"
    ) -> bool:
        popup = Toplevel(self)
        popup.title(title)
        popup.resizable(False, False)
        popup.iconbitmap(Icons.DEFAULT)

        Label(popup, text=message, wraplength=280).pack(padx=20, pady=10)

        button_frame = Frame(popup)
        button_frame.pack(pady=10)

        def on_ok():
            popup.destroy()

        def on_custom():
            custom_callback()
            popup.destroy()

        ok_button = Button(button_frame, text=ok, command=on_ok)
        ok_button.bind("<Return>", lambda e: e.widget.invoke())
        ok_button.bind("<Escape>", lambda e: on_ok())
        ok_button.pack(side="left", padx=10)

        custom_button = Button(button_frame, text=custom, command=on_custom)
        custom_button.bind("<Return>", lambda e: e.widget.invoke())
        custom_button.bind("<Escape>", lambda e: on_ok())
        custom_button.pack(side="right", padx=10)

        popup.transient(self)
        popup.grab_set()
        self.center_window(popup)
        ok_button.focus_set()
        self.wait_window(popup)

    def popup_integer(
        self,
        title: str,
        prompt: str,
        minvalue: int = None,
        maxvalue: int = None,
        initialvalue: int = None,
    ) -> int:
        """
        Displays a popup window to ask for an integer input.

        Args:
            title (str): The title of the popup window.
            prompt (str): The prompt message.
            minvalue (int, optional): The minimum value. Defaults to None.
            maxvalue (int, optional): The maximum value. Defaults to None.
            initialvalue (int, optional): The initial value. Defaults to None.

        Returns:
            int: The integer input from the user.
        """
        result = IntVar(value=initialvalue)

        popup = Toplevel(self)
        popup.title(title)
        popup.resizable(False, False)
        popup.iconbitmap(Icons.ASK)

        Label(popup, text=prompt, wraplength=280).pack(padx=20, pady=10)

        entry = Entry(popup, textvariable=result)
        entry.pack(padx=20, pady=10)
        entry.focus_set()

        def on_ok():
            try:
                value = int(entry.get())
                if (minvalue is not None and value < minvalue) or (
                    maxvalue is not None and value > maxvalue
                ):
                    raise ValueError
                result.set(value)
                popup.destroy()
            except ValueError:
                entry.delete(0, "end")
                entry.insert(0, initialvalue if initialvalue is not None else "")

        def on_cancel():
            result.set(None)
            popup.destroy()

        button_frame = Frame(popup)
        button_frame.pack(pady=10)

        entry.bind("<Return>", lambda e: on_ok())

        ok_button = Button(button_frame, text="OK", command=on_ok)
        ok_button.bind("<Return>", lambda e: e.widget.invoke())
        ok_button.bind("<Escape>", lambda e: on_cancel())
        ok_button.pack(side="left", padx=10)

        cancel_button = Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.bind("<Return>", lambda e: e.widget.invoke())
        cancel_button.bind("<Escape>", lambda e: on_cancel())
        cancel_button.pack(side="right", padx=10)

        popup.transient(self)
        popup.grab_set()
        self.center_window(popup)
        self.wait_window(popup)

        return result.get()

    def popup_string(self, title: str, prompt: str, initialvalue: str = "") -> str:
        """
        Displays a popup window to ask for a string input.

        Args:
            title (str): The title of the popup window.
            prompt (str): The prompt message.
            initialvalue (str, optional): The initial value. Defaults to "".

        Returns:
            str: The string input from the user.
        """
        result = StringVar(value=initialvalue)

        popup = Toplevel(self)
        popup.title(title)
        popup.resizable(False, False)
        popup.iconbitmap(Icons.ASK)

        Label(popup, text=prompt, wraplength=280).pack(padx=20, pady=10)

        entry = Entry(popup, textvariable=result)
        entry.pack(padx=20, pady=10)
        entry.focus_set()

        def on_ok():
            popup.destroy()

        def on_cancel():
            result.set(None)
            popup.destroy()

        button_frame = Frame(popup)
        button_frame.pack(pady=10)

        entry.bind("<Return>", lambda e: on_ok())

        ok_button = Button(button_frame, text="OK", command=on_ok)
        ok_button.bind("<Return>", lambda e: e.widget.invoke())
        ok_button.bind("<Escape>", lambda e: on_cancel())
        ok_button.pack(side="left", padx=10)

        cancel_button = Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.bind("<Return>", lambda e: e.widget.invoke())
        cancel_button.bind("<Escape>", lambda e: on_cancel())
        cancel_button.pack(side="right", padx=10)

        popup.transient(self)
        popup.grab_set()
        self.center_window(popup)
        self.wait_window(popup)

        return result.get()

    def popup_list(
        self,
        title: str,
        message: str,
        options: dict[str, str],
        default: str | None = None,
    ) -> str:
        """
        Displays a popup window with a list of options.

        Args:
            title (str): The title of the popup window.
            message (str): The message to display.
            options (dict[str, str]): The options to display.
            default (str | None, optional): The default option. Defaults to None.

        Returns:
            str: The selected option.
        """
        result = StringVar(value="")

        popup = Toplevel(self)
        popup.title(title)
        popup.configure(width=480)
        popup.resizable(False, False)
        popup.iconbitmap(Icons.ASK)

        Label(popup, text=message, wraplength=280).pack(padx=20, pady=10)

        list_frame = Frame(popup)
        list_frame.pack(pady=10, padx=10, fill="x")

        option_list = Listbox(list_frame, height=10, selectmode="single")
        for option in options:
            option_list.insert("end", option)
        option_list.pack(side="left", fill="y")

        detail_frame = Frame(list_frame)
        detail_frame.pack(side="left", padx=10, fill="both", expand=True)

        detail_label = Text(detail_frame, wrap="word", height=10, state="disabled")
        detail_label.pack(side="left", fill="both", expand=True)

        scrollbar = Scrollbar(detail_frame, command=detail_label.yview)
        scrollbar.pack(side="right", fill="y")
        detail_label.config(yscrollcommand=scrollbar.set)

        def on_select():
            detail_label.config(state="normal")
            detail_label.delete(1.0, "end")
            detail_label.insert(
                "end", options[option_list.get(option_list.curselection())]
            )
            detail_label.config(state="disabled")

        def on_option():
            result.set(option_list.get(option_list.curselection()))
            popup.destroy()

        def on_cancel():
            result.set(option_list.get("end"))
            popup.destroy()

        option_list.bind("<<ListboxSelect>>", lambda e: on_select())
        option_list.bind("<Return>", lambda e: on_option())
        option_list.bind("<Escape>", lambda e: on_cancel())

        button_frame = Frame(popup)
        button_frame.pack(pady=10)

        select_button = Button(button_frame, text="Select", command=on_option)
        select_button.bind("<Return>", lambda e: e.widget.invoke())
        select_button.bind("<Escape>", lambda e: on_cancel())
        select_button.pack(padx=10)

        popup.transient(self)
        popup.grab_set()
        self.center_window(popup)
        option_list.focus_set()
        index = (
            list(options.keys()).index(default)
            if default and default in options
            else "end"
        )
        option_list.select_set(index)
        option_list.see(index)
        on_select()
        self.wait_window(popup)

        return result.get()

    def edit_settings(self):
        """
        Displays a window to edit the system message and other settings.
        """
        edit_window = Toplevel(self)
        edit_window.title("Edit System Message")
        edit_window.resizable(False, False)
        edit_window.iconbitmap(Icons.DEFAULT)

        settings_frame = Frame(edit_window)
        settings_frame.pack(padx=10, pady=10, fill="both", expand=True)

        model_frame = Frame(settings_frame)
        model_frame.pack(fill="x", pady=5)
        Label(model_frame, text="Model:").pack(side="left")
        model_var = StringVar(value=self.model)
        model_entry = Entry(
            model_frame,
            textvariable=model_var,
            state="disabled",
        )
        model_entry.pack(side="right", fill="x", expand=True, padx=10)

        personality_frame = Frame(settings_frame)
        personality_frame.pack(fill="x", pady=5)
        Label(personality_frame, text="Personality:").pack(side="left")
        personality_var = StringVar(value=self.personality)
        personality_combobox = Combobox(
            personality_frame,
            textvariable=personality_var,
            values=list(PERSONALITIES.keys()),
            state="readonly",
        )
        personality_combobox.pack(side="right", fill="x", expand=True, padx=10)
        if not self.current_session:
            personality_combobox.configure(state="disabled")

        system_message_frame = Frame(settings_frame)
        system_message_frame.pack(fill="x", pady=5)
        Label(system_message_frame, text="Additional System Prompt:").pack(side="left")
        system_message_var = StringVar(value=self.add_sys_msg)
        system_entry = Entry(
            system_message_frame, textvariable=system_message_var, width=50
        )
        system_entry.pack(side="right", fill="x", expand=True, padx=10)

        max_tokens_frame = Frame(settings_frame)
        max_tokens_frame.pack(fill="x", pady=5)
        Label(max_tokens_frame, text="Max Tokens:").pack(side="left")
        max_tokens_var = IntVar(value=self.max_tokens)
        max_tokens_entry = Entry(
            max_tokens_frame, textvariable=max_tokens_var, width=50
        )
        max_tokens_entry.bind(
            "<KeyPress>",
            lambda e: (
                "break"
                if not (e.char.isdigit() or e.keysym in ["Left", "Right", "BackSpace"])
                else None
            ),
        )
        max_tokens_entry.pack(side="right", fill="x", expand=True, padx=10)

        def save_edits():
            self.add_sys_msg = system_message_var.get().strip()
            self.max_tokens = max_tokens_var.get()
            self.personality = personality_var.get()

            self.popup_info("Updated", "Settings updated successfully!")
            edit_window.destroy()

        save_button = Button(edit_window, text="Save", command=save_edits)
        save_button.pack(pady=10)

        if self.lite_mode:
            model_entry.configure(state="disabled")
            system_entry.configure(state="disabled")

        edit_window.transient(self)
        edit_window.grab_set()
        self.center_window(edit_window)
        self.input_box.focus_set()

    def open_folder(self, folder: str):
        """
        Opens a folder in the default file manager.

        Args:
            folder (str): The path to the folder.
        """
        if not path.exists(folder):
            self.popup_info("Error", "Folder does not exist.", True)
            return

        sysname = systemname().casefold()

        if sysname == "windows":
            # Popen(f'explorer "{folder}"')
            startfile(path.normpath(folder), "open")
        elif sysname == "darwin":
            Popen(["open", folder])
        else:
            try:
                Popen(["xdg-open", folder])
            except:
                self.popup_info(
                    "Error",
                    "Could not run xdg-open. The following path was attempted to open:\n{folder}.",
                    True,
                )


if __name__ == "__main__":
    try:
        openai = OpenAI()
    except OpenAIError as e:
        from tkinter.messagebox import showerror

        showerror("OpenAI Error", f"An error occurred while initializing OpenAI: {e}")
        exit(1)
    app = MyPyGPTClient()
    app.mainloop()
