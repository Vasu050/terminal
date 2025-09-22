import os
import subprocess
import shutil
import psutil
import google.generativeai as genai
import shlex 


def main():
  
    dir_history = [os.getcwd()]
    dir_index = 0
    try:
        while True:
            prompt = f"my-shell:{os.getcwd()}$ "
            command = input(prompt)

            if not command.strip():
                continue

            if command.lower() == "exit":
                break
            
            # --- CHANGE 2: Use shlex.split() for proper argument parsing ---
            try:
                parts = shlex.split(command)
            except ValueError:
                print("Error: Unmatched quotes in command.")
                continue
            # -----------------------------------------------------------------

            cmd = parts[0]
            args = parts[1:]

            # Keyword matching for undo/redo navigation
            lower_cmd = command.lower() # Use original command for keyword matching
            undo_keywords = ["undo", "back", "go back", "previous", "go to previous", "return"]
            redo_keywords = ["redo", "forward", "go forward", "next", "go to next"]
            
            if any(k in lower_cmd for k in undo_keywords):
                if dir_index > 0:
                    dir_index -= 1
                    os.chdir(dir_history[dir_index])
                    print(f"Went back to: {os.getcwd()}")
                else:
                    print("No previous directory in history.")
                continue
            elif any(k in lower_cmd for k in redo_keywords):
                if dir_index < len(dir_history) - 1:
                    dir_index += 1
                    os.chdir(dir_history[dir_index])
                    print(f"Went forward to: {os.getcwd()}")
                else:
                    print("No next directory in history.")
                continue

            # Native commands
            if cmd == "pwd":
                print(os.getcwd())
            elif cmd == "cd":
                target_dir = args[0] if args else os.path.expanduser("~")
                try:
                    os.chdir(target_dir)
                    if dir_index == len(dir_history) - 1:
                        dir_history.append(os.getcwd())
                        dir_index += 1
                    else:
                        dir_history = dir_history[:dir_index + 1] + [os.getcwd()]
                        dir_index += 1
                    print(f"Changed directory to: {os.getcwd()}")
                except FileNotFoundError:
                    print(f"cd: no such directory: {target_dir}")
                except Exception as e:
                    print(f"cd: {e}")
            elif cmd == "ls":
                try:
                    path = args[0] if args else os.getcwd()
                    for entry in os.listdir(path):
                        print(entry)
                except Exception as e:
                    print(f"ls: {e}")
            elif cmd == "mkdir":
                if not args:
                    print("mkdir: missing operand")
                else:
                    try:
                        os.mkdir(args[0])
                        print(f"Created directory: {args[0]}")
                    except Exception as e:
                        print(f"mkdir: {e}")
            elif cmd == "mv":
                if len(args) < 2:
                    print("mv: missing source or destination operand")
                else:
                    # Now handles multiple sources, moving them to the last argument
                    destination = args[-1]
                    sources = args[:-1]
                    for src in sources:
                        try:
                            shutil.move(src, destination)
                            print(f"Successfully moved '{src}' to '{destination}'")
                        except Exception as e:
                            print(f"mv: Failed to move '{src}': {e}")
            elif cmd == "rm":
                if not args:
                    print("rm: missing operand")
                else:
                    path = args[0]
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                        print(f"Removed: {path}")
                    except Exception as e:
                        print(f"rm: {e}")
            # ... (cpu, mem, ps commands are the same) ...
            elif cmd == "cpu":
                try:
                    print(f"CPU Usage: {psutil.cpu_percent()}%")
                except Exception as e:
                    print(f"cpu: {e}")
            elif cmd == "mem":
                try:
                    mem = psutil.virtual_memory()
                    print(f"Memory Usage: {mem.percent}% ({mem.used // (1024**2)}MB/{mem.total // (1024**2)}MB)")
                except Exception as e:
                    print(f"mem: {e}")
            elif cmd == "ps":
                try:
                    for proc in psutil.process_iter(['pid', 'name']):
                        print(f"{proc.info['pid']}: {proc.info['name']}")
                except Exception as e:
                    print(f"ps: {e}")
            else:
                ai_command_str = generate_command_from_message(command)
                if ai_command_str:
                    try:
                        # Also use shlex for the AI's output
                        ai_parts = shlex.split(ai_command_str)
                        # Now you can handle the AI command using the same logic as native commands
                        # This part can be refactored later to avoid repetition
                        ai_cmd = ai_parts[0]
                        ai_args = ai_parts[1:]
                        if ai_cmd == "mv":
                            if len(ai_args) < 2:
                                print("mv: missing source or destination operand")
                            else:
                                destination = ai_args[-1]
                                sources = ai_args[:-1]
                                for src in sources:
                                    try:
                                        shutil.move(src, destination)
                                        print(f"Successfully moved '{src}' to '{destination}'")
                                    except Exception as e:
                                        print(f"mv: Failed to move '{src}': {e}")
                        else: # Fallback for other AI commands like git, etc.
                            subprocess.run(ai_command_str, shell=True)
                    except Exception as e:
                        print(f"Error executing AI command: {e}")
                else:
                    print(f"Unrecognized command: {command}")

    except KeyboardInterrupt:
        print("\nSession terminated.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


# --- AI Configuration and Helper Functions ---

try:
    genai.configure(api_key="AIzaSyBHjWkesJU3oFXrXVkwUGOrpQIlWea9WsM")
    model = genai.GenerativeModel("models/gemini-1.5-flash")
except Exception as e:
    model = None
    print(f"Could not configure AI model. AI features will be disabled. Error: {e}")

def gemini_generate(prompt: str) -> str:
    # ... (this function remains the same)
    if not model: return ""
    try:
        content = model.generate_content(prompt)
        return content.text.strip()
    except Exception as e:
        print(f"Error communicating with AI model: {e}")
        return ""

def generate_command_from_message(user_message: str) -> str:
    # --- CHANGE 3: Improved AI Prompt ---
    prompt = f"""
You are an AI assistant for a command-line terminal. Convert the user's request into a single, executable shell command.
- If the request is to move or rename, use the 'mv' command format: mv "source" "destination".
- If the user says to move a file "to folder X" or "into X", the destination in the command should just be "X".
- Only return the command itself, with no explanation, markdown, or conversational text.
- If the request is not a valid file, directory, process, or system command, output nothing.

User Message: "{user_message}"
Shell Command:"""
    raw_output = gemini_generate(prompt)
    if raw_output.startswith("`") and raw_output.endswith("`"):
        raw_output = raw_output.strip("`")
    return raw_output.strip()


# --- Script Entry Point ---

if __name__ == "__main__":
    main()