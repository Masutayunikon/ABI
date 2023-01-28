import os
from time import sleep

import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
import mss
import threading
import pyautogui
import keyboard

start = False
last_clicked = None
rules = []
thread_started = False
current_thread = None
percentage_to_win = None
stop_flag = threading.Event()


def compare(image1, image2):
    image1 = image1.convert("RGBA")
    image2 = image2.convert("RGBA")
    # Superpose the two images
    superposed_image = Image.alpha_composite(image1, image2)

    # save the superposed image
    superposed_image.save('screenshots/superposed_image.png')

    # Get the pixel data from both images as numpy arrays
    image1_data = np.array(image1)
    superposed_image_data = np.array(superposed_image)

    # Compare the pixel data of the two images
    same_pixels = np.sum(np.all(image1_data == superposed_image_data, axis=-1))
    total_pixels = image1_data.shape[0] * image1_data.shape[1]
    percentage_same = same_pixels / total_pixels * 100
    return percentage_same


def image_recognition():
    global start
    start = True

    rule_layers = []
    default_touch_is_pressed = False
    default_touch_to_press = None
    last_touch_down = None

    for rule in rules:
        if rule['name'] == 'default':
            default_touch_to_press = {"touch": rule['input'].get(), "press": rule['press'].get(), "single": rule['single'].get()}
            continue
        path = 'screenshots/' + rule['name'] + '/layer.png'
        if os.path.exists(path):
            rule_layers.append({"image": Image.open(path), "touch": rule['input'].get(), "name": rule['name'],
                                 "press": rule['press'].get(), "single": rule['single'].get()})

    while not stop_flag.is_set():
        print('loop')
        # take screenshot and load it in a variable
        with mss.mss() as sct:
            sct.shot(output='screenshots/screenshot.png')
            screenshot = Image.open('screenshots/screenshot.png')
            # for each layer in the layers list get the best percentage
            current_percent = None
            winner_rule = None
            min_percentage = percentage_to_win.get()
            # check if min percentage is a number
            try:
                min_percentage = float(min_percentage)
            except ValueError:
                min_percentage = 80

            for rule in rule_layers:
                print('rule loop')
                if current_percent is None:
                    new_percentage = compare(screenshot, rule['image'])
                    if new_percentage > min_percentage:
                        current_percent = new_percentage
                        winner_rule = rule
                else:
                    new_percentage = compare(screenshot, rule['image'])
                    if new_percentage > current_percent and new_percentage > min_percentage:
                        current_percent = new_percentage
                        winner_rule = rule
            if winner_rule is not None:
                print(winner_rule['name'])
                # check if default touch is pressed
                if default_touch_is_pressed:
                    pyautogui.keyUp(default_touch_to_press['touch'])
                    default_touch_is_pressed = False
                    # check if winner touch need to be pressed or not
                if winner_rule['touch'] is not None:
                    # check if winner touch have a length
                    if len(winner_rule['touch']) > 0:
                        # check if winner touch is not a number
                        if winner_rule['single']:
                            if last_touch_down is not None:
                                pyautogui.keyUp(last_touch_down)
                                last_touch_down = None
                            pyautogui.press(winner_rule['touch'])
                        else:
                            pyautogui.keyDown(winner_rule['touch'])
                            last_touch_down = winner_rule['touch']

            # else if default touch is not pressed press it
            elif winner_rule is None and not default_touch_is_pressed:
                if default_touch_to_press['touch'] is not None:
                    # check if default touch have a length
                    if len(default_touch_to_press['touch']) > 0:
                        if last_touch_down is not None:
                            pyautogui.keyUp(last_touch_down)
                            last_touch_down = None
                        # check if default touch is not a number
                        if default_touch_to_press['single']:
                            pyautogui.keyDown(default_touch_to_press['touch'])
                            pyautogui.keyUp(default_touch_to_press['touch'])
                        else:
                            pyautogui.keyDown(default_touch_to_press['touch'])
                            default_touch_is_pressed = True

    print('end loop')
    return 0


def start_reco():
    global thread_started
    global current_thread
    stop()

    thread_started = True
    stop_flag.clear()
    current_thread = threading.Thread(target=image_recognition)
    current_thread.start()
    print('thread started')


def stop():
    global thread_started
    global current_thread
    if thread_started and current_thread is not None:
        thread_started = False
        stop_flag.set()
        print('thread stopped ? : ' + str(current_thread.is_alive()))
        current_thread = None


def create_layer(current_directory):
    image_files = [f for f in os.listdir(current_directory) if
                   f.endswith('.jpg') or f.endswith('.png') and f != 'layer.png']
    if len(image_files) == 1:
        result = Image.open(current_directory + '/' + image_files[0])
        result.save(current_directory + '/layer.png')
        return result
    # open all images in images
    images = [Image.open(current_directory + '/' + f) for f in image_files]

    pixels_array = [list(image.getdata()) for image in images]
    result = [
        list(set([pixels_array[j][i] for j in range(len(pixels_array))]))[0] if len(
            set([pixels_array[j][i] for j in range(len(pixels_array))])) == 1 else (0, 0, 0, 0)
        for i in range(len(pixels_array[0]))
    ]
    result_image = Image.new("RGBA", images[0].size)
    result_image.putdata(result)
    result_image.save(current_directory + '/layer.png')

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
        new_image = create_layer('screenshots/' + name)
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


def set_keyboard_combo(tk_root, current_button, label_image, label, name):
    global last_clicked
    if last_clicked:
        last_clicked.config(bg='SystemButtonFace')
    current_button.config(bg='red')
    last_clicked = current_button
    while not stop_flag.is_set():
        if keyboard.is_pressed('ctrl+p'):
            print('keyboard combo pressed')
            add_image(label_image, label, name)
            sleep(2)


def start_thread(tk_root, current_button, label_image, label, name):
    global thread_started
    global current_thread
    global start
    if start:
        return
    if not thread_started:
        thread_started = True
        stop_flag.clear()
        current_thread = threading.Thread(target=set_keyboard_combo,
                                          args=(tk_root, current_button, label_image, label, name))
        current_thread.start()
        print('thread started')
    else:
        print('thread already started')
        thread_started = False
        stop_flag.set()
        current_thread.join()
        print('thread stopped')
        start_thread(tk_root, current_button, label_image, label, name)


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

    # add border to the frame
    frame.config(relief=tk.RAISED, borderwidth=3)

    # set border color
    frame.config(bg='black')

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


    input_text = tk.Entry(main_frame, font=('Arial', 12), textvariable=input_var)
    input_text.grid(row=1, column=1)

    input_text.bind("<FocusIn>", on_focus_in)
    input_text.bind("<FocusOut>", on_focus_out)


    def create_rule():
        name = input_text.get()

        if ' ' in name:
            name = name.replace(' ', '_')

        if not name or name in rules:
            return

        # make directory for the rule in the screenshots directory
        os.makedirs("./" + directory + "/" + name)

        # create a rule_frame in frame who take all horizontal space
        rule_frame = tk.Frame(rules_frame)
        rule_frame.pack(fill=tk.X, expand=True, pady=5)
        rule_frame.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        label = tk.Label(rule_frame, text=name + ' (0)', font=('Arial', 10))
        label.pack(side=tk.LEFT, padx=5, pady=5)

        photo = ImageTk.PhotoImage(Image.open('default.png').resize((100, 100)))
        label_image = tk.Label(rule_frame, image=photo, bg='black')
        label_image.image = photo

        rule_button = tk.Button(rule_frame, text='Select', font=('Arial', 12),
                                command=lambda: start_thread(root, rule_button, label_image, label, name))
        label_image.pack(side=tk.LEFT, padx=5, pady=5)
        rule_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # create a label "touch" and an input for touch after this add two checkbox long press and single press
        touch_label = tk.Label(rule_frame, text='Touch', font=('Arial', 10))
        touch_label.pack(side=tk.LEFT, padx=5, pady=5)

        input_touch = tk.Entry(rule_frame, font=('Arial', 12))
        input_touch.pack(side=tk.LEFT, padx=5, pady=5)

        long_press = tk.IntVar()
        long_press.set(1)

        single_press = tk.IntVar()
        single_press.set(0)

        long_press_checkbox = tk.Checkbutton(rule_frame, text='Long press', variable=long_press, font=('Arial', 10))
        long_press_checkbox.pack(side=tk.LEFT, padx=5, pady=5)

        single_press_checkbox = tk.Checkbutton(rule_frame, text='Single press', variable=single_press,
                                               font=('Arial', 10))
        single_press_checkbox.pack(side=tk.LEFT, padx=5, pady=5)

        # if long press is checked unchecked the other
        def long_press_check():
            if long_press.get():
                single_press.set(0)
            else:
                single_press.set(1)

        # if single press is checked unchecked the other
        def single_press_check():
            if single_press.get():
                long_press.set(0)
            else:
                long_press.set(1)

        long_press_checkbox.config(command=long_press_check)
        single_press_checkbox.config(command=single_press_check)

        rules.append({"input": input_touch, "name": name, "press": long_press, "single": single_press})

        input_text.delete(0, tk.END)

        canvas.config(scrollregion=canvas.bbox(tk.ALL))


    def on_closing():
        stop_flag.set()
        root.destroy()


    button = tk.Button(main_frame, text='Add rule', command=create_rule)
    button.grid(row=1, column=2)

    # add label and input for default touch and two checkbox for up or down with label before to describe the checkbox
    default_touch_label = tk.Label(main_frame, text='Default touch', font=('Arial', 10))
    default_touch_label.grid(row=1, column=3)

    default_touch = tk.Entry(main_frame, font=('Arial', 12))
    default_touch.grid(row=1, column=4)

    default_touch_up = tk.IntVar()
    default_touch_up.set(1)

    default_touch_up_checkbox = tk.Checkbutton(main_frame, text='Single press', variable=default_touch_up)
    default_touch_up_checkbox.grid(row=1, column=5)

    default_touch_down = tk.IntVar()
    default_touch_down.set(0)

    default_touch_down_checkbox = tk.Checkbutton(main_frame, text='Long press', variable=default_touch_down)
    default_touch_down_checkbox.grid(row=1, column=6)


    def check_up():
        if default_touch_up.get() == 1:
            default_touch_down.set(0)
        else:
            default_touch_down.set(1)


    def check_down():
        if default_touch_down.get() == 1:
            default_touch_up.set(0)
        else:
            default_touch_up.set(1)


    default_touch_up_checkbox.config(command=check_up)
    default_touch_down_checkbox.config(command=check_down)

    rules.append({"name": "default", "input": default_touch, "press": default_touch_up, "single": default_touch_down})

    start_button = tk.Button(main_frame, text='Start',
                             command=start_reco)
    start_button.grid(row=1, column=7)

    stop_button = tk.Button(main_frame, text='Stop', command=stop)
    stop_button.grid(row=1, column=8)

    # add label named "Percentage of similarity minimum" and an input for the percentage who accept just number
    percentage_label = tk.Label(main_frame, text='Percentage of similarity minimum', font=('Arial', 10))
    percentage_label.grid(row=1, column=9)

    percentage = tk.Entry(main_frame, font=('Arial', 12))
    percentage.grid(row=1, column=10)

    percentage.insert(0, 80)

    percentage.bind('<KeyRelease>',
                    lambda event: percentage.delete(0, tk.END) if not percentage.get().isdigit() else None)

    percentage_to_win = percentage

    root.protocol("WM_DELETE_WINDOW", on_closing)

    tk.mainloop()
