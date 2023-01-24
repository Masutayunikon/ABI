import os
from time import sleep

from PIL import Image, ImageTk
import tkinter as tk
import mss
import threading
import keyboard
import concurrent.futures
import numpy as np

last_clicked = None
rules = []
thread_started = False
current_thread = None
stop_flag = threading.Event()


def create_calque(directory):
    image_files = [f for f in os.listdir(directory) if f.endswith('.jpg') or f.endswith('.png') and f != 'calque.png']
    with concurrent.futures.ThreadPoolExecutor() as executor:
        images = list(executor.map(Image.open, [os.path.join(directory, f) for f in image_files]))
    width, height = images[0].size
    numpy_images = np.array([np.array(img) for img in images])
    result_image = numpy_images[0]
    result_image[np.where(~np.all(numpy_images==result_image,axis=0))] = 0
    result_image = Image.fromarray(result_image.astype(np.uint8))
    result_image.save(os.path.join(directory, 'calque.png'))
    return result_image


def add_image(image, label, name):
    print('add image')
    # take screenshot
    with mss.mss() as sct:
        # create random sha-1 hash and convert to string
        hashed = os.urandom(20).hex()
        # create file name
        filename = f'{hashed}.png'
        sct.shot(output='screenshots/' + name + '/' + filename)
    print('add image')
    try:
        new_image = create_calque('screenshots/' + name)
        # resize image
        print('add image')
        new_image = ImageTk.PhotoImage(new_image.resize((100, 100)))
        # update image
        image.configure(image=new_image)
        image.image = new_image

        # update label text to show number of images
        label.configure(text=f'{name} ({len(os.listdir("screenshots/" + name)) - 1})')
    except Exception as e:
        print(e)
    print('add image')


def set_keyboard_combo(tk_root, button, label_image, label, name):
    global last_clicked
    if last_clicked:
        last_clicked.config(bg='SystemButtonFace')
    button.config(bg='red')
    last_clicked = button
    while not stop_flag.is_set():
        if keyboard.is_pressed('ctrl+p'):
            print('keyboard combo pressed')
            add_image(label_image, label, name)
            sleep(2)


def start_thread(tk_root, button, label_image, label, name):
    global thread_started
    global current_thread
    if not thread_started:
        thread_started = True
        stop_flag.clear()
        current_thread = threading.Thread(target=set_keyboard_combo, args=(tk_root, button, label_image, label, name))
        current_thread.start()
        print('thread started')
    else:
        print('thread already started')
        thread_started = False
        stop_flag.set()


if __name__ == '__main__':
    # Create a directory to store the screenshots
    directory = 'screenshots'
    if not os.path.exists(directory):
        os.makedirs("./" + directory)

    # remove all files and directories in the screenshots directory
    for file in os.listdir(directory):
        if os.path.isdir(directory + '/' + file):
            for f in os.listdir(directory + '/' + file):
                os.remove(directory + '/' + file + '/' + f)
            os.rmdir(directory + '/' + file)
        else:
            os.remove(directory + '/' + file)

    # Create a tkinter window
    root = tk.Tk()
    # set window size
    # get screen width and height
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.geometry(f'{width}x{height}')
    # create the main frame
    main_frame = tk.Frame(root)

    main_frame.pack(fill=tk.BOTH, expand=True)

    for i in range(100):
        main_frame.columnconfigure(i, weight=1)
        main_frame.rowconfigure(i, weight=1)

    # create a frame in row 5 and column 5 who take 90 column and 90 row

    frame = tk.Frame(main_frame)
    frame.grid(row=5, column=1, rowspan=92, columnspan=98, sticky='nsew')

    canvas = tk.Canvas(frame)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

    rules_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=rules_frame, anchor='nw')

    # create input for text
    placeholder = "Name of your rule"
    input_var = tk.StringVar()
    input_var.set(placeholder)


    def on_focus_in(event):
        if input_var.get() == placeholder:
            input_var.set("")


    def on_focus_out(event):
        if input_var.get() == "":
            input_var.set(placeholder)


    input_text = tk.Entry(main_frame, font=('Arial', 14), textvariable=input_var)
    input_text.grid(row=1, column=1)

    input_text.bind("<FocusIn>", on_focus_in)
    input_text.bind("<FocusOut>", on_focus_out)


    def create_rule():
        name = input_text.get()

        if ' ' in name:
            name = name.replace(' ', '_')

        if not name or name in rules:
            return

        rules.append(name)

        # make directory for the rule in the screenshots directory
        os.makedirs("./" + directory + "/" + name)

        # create a rule_frame in frame who take all horizontal space
        rule_frame = tk.Frame(rules_frame)
        rule_frame.pack(fill=tk.X, expand=True, pady=5)
        rule_frame.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        label = tk.Label(rule_frame, text=name + ' (0)', font=('Arial', 14))
        label.pack(side=tk.LEFT, padx=5, pady=5)

        photo = ImageTk.PhotoImage(Image.open('default.png').resize((100, 100)))
        label_image = tk.Label(rule_frame, image=photo, bg='black')
        label_image.image = photo

        rule_button = tk.Button(rule_frame, text='Select', font=('Arial', 14),
                                command=lambda: start_thread(root, rule_button, label_image, label, name))
        rule_button.pack(side=tk.RIGHT, padx=5, pady=5)

        label_image.pack()

        input_text.delete(0, tk.END)

        canvas.config(scrollregion=canvas.bbox(tk.ALL))


    def on_closing():
        stop_flag.set()
        root.destroy()


    button = tk.Button(main_frame, text='Add rule', command=create_rule)
    button.grid(row=1, column=2)

    # add input only for number
    input_number = tk.Entry(main_frame, font=('Arial', 14))
    input_number.grid(row=1, column=3)
    # check if the input is a number
    input_number.bind('<KeyRelease>', lambda event: input_number.delete(0, tk.END) if not input_number.get().isdigit() else None)

    start_button = tk.Button(main_frame, text='Start', command=lambda: start_thread(root, start_button, None, None, None))
    start_button.grid(row=1, column=4)

    root.protocol("WM_DELETE_WINDOW", on_closing)

    tk.mainloop()
