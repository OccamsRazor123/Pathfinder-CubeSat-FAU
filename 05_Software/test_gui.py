import tkinter as tk

print("Attempting to start GUI...")

try:
    root = tk.Tk()
    root.title("Tkinter Test")
    root.geometry("300x200")
    
    # FIX: changed pad_x to padx, pad_y to pady (removed underscores)
    label = tk.Label(root, text="If you can see this, tkinter is working!", padx=20, pady=20)
    label.pack()
    
    print("GUI window should be open now. Look for it.")
    
    root.mainloop()
    
    print("GUI window was closed.")

except Exception as e:
    print(f"ERROR: Failed to run GUI. The error was: {e}")