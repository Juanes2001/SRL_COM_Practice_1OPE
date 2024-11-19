import sys, os, time
import platform
from random import randint
from turtledemo.paint import switchupdown

import serial, serial.tools.list_ports
#from PySide2.QtSerialPort import readData
# interface import
from PySide2.QtWidgets import QApplication, QMainWindow, QDesktopWidget, QTextEdit, QLineEdit, QPushButton, QMessageBox, \
    QWidget, QGridLayout, QTextEdit, QGroupBox, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from PySide2.QtGui import QIcon, QScreen
# from PySide2.examples.tutorial.t10 import widget
from ipywidgets import widget_serialization
from numpy.core.numeric import False_

from serial.serialutil import SerialException

import threading
import plotly.graph_objects as go
import numpy as np

## EN ESTA PARTE DE CODIGO SE TENDRA EL PLOTEO EN TIEMPO REAL

def responsivity(x,y):
    if (x<475):
        return 2.5*y
    # elif (x>=425 and x<450):
    # return y/(0.003*x-1.225)
    elif (x>=475 and x<500):
        return y/(0.0145*x-6.4)
    elif (x>=500 and x<512.5):
        return y/(0.004*x-1.15)
    elif (x>=512.5 and x<550):
        return y/(-0.0027*x+2.27)
    elif (x>=550 and x<575):
        return y/(0.008*x-3.6)
    elif (x>=575 and x<625):
        return y/(-0.006*x+4.45)
    elif (x>=625 and x<650):
        return y/(-0.0087*x+6.12)
    else:
        return 2.5*y


layout = go.Layout(
                title="Espectro LED Blanco",
                plot_bgcolor="#FFFFFF",
                hovermode="x",
                hoverdistance=100, # Distance to show hover label of data point
                spikedistance=1000, # Distance to show spike
                xaxis=dict(
                title="Longitud de onda (nm)",
                linecolor="#BCCCDC",
                showspikes=True, # Show spike line for X-axis
                # Format spike
                spikethickness=2,
                spikedash="dot",
                spikecolor="#999999",
                spikemode="across",
                ),

                yaxis=dict(
                title="Intensidad Relativa (lux)",
                linecolor="#BCCCDC"
                )
                )
fig = go.FigureWidget(layout=layout)
fig.add_scatter()

lastLen = 0



outListx = []
outListy = []
start_measurements_state = False
command_parsed = False
step_motor_state = False


#////////////////////////////////////////////////////////////////////////////////////#



# With this we find the used USB ports saved in the computer.
def find_USB_device():
    myports = [tuple(p) for p in list(serial.tools.list_ports.comports())]
    print(myports)
    usb_port_list = [p[0] for p in myports]

    return usb_port_list


class SerialInterface(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.width = 650
        self.height = 350

        self.resize(self.width, self.height)
        self.setWindowIcon(QIcon('C:/Users/juane/OneDrive/Pictures/Saved Pictures/Logo.png'))
        self.setWindowTitle('Serial Monitor')

        # center window on screen
        qr = self.frameGeometry()
        cp = QScreen().availableGeometry().center()
        qr.moveCenter(cp)

        # init layout
        centralwidget = QWidget(self)
        centralLayout = QHBoxLayout(centralwidget)
        self.setCentralWidget(centralwidget)

        # add connect group
        self.connectgrp = GroupClass(self)
        centralLayout.addWidget(self.connectgrp)


class GroupClass(QGroupBox):
    def __init__(self, widget, title="Connection Configuration"):
        super().__init__(widget)
        self.widget = widget
        self.title = title
        self.sep = "-"
        self.id = -1
        self.name = ''
        self.items = find_USB_device()
        self.serial = None
        self.init()
        readThread = threading.Thread(name='Read', target=self.read_Data)
        plotThread = threading.Thread(name='Plot', target=self.plot, args=(fig,), daemon=True)
        prove = threading.Thread(name='Prove', target=self.read_Data)

    def refreshPorts(self):
        # Update the list of available ports
        self.items = find_USB_device()
        self.typeBox.clear()
        self.typeBox.addItems(self.items)
        if self.items:
            self.desc.setText(">> Ports list updated.\n")
            time.sleep(1)
            self.desc.setText(">> Ready to reconnect\n")
        else:
            self.desc.setText("No available ports detected.")

    def clearTypeBox(self):
        self.desc.clear()

    def plot(self,fig):
        global outListx
        global outListy
        while (1):
            datay = np.array(outListy)
            datax = (11. / 26.) * (np.array(outListx) - 200) + 400
            for i in range(len(datay)):
                datay[i] = responsivity(datax[i], datay[i])
            fig.data[0].y = datay[:]
            fig.data[0].x = datax[:]
            time.sleep(1)
        return


    def connect(self):

        if self.serial is None:

            self.desc.setText("")
            self.desc.setText(">> trying to connect to port %s ..." % self.typeBox.currentText())

            try:
                self.serial = serial.Serial(self.typeBox.currentText(), 115200, timeout=1)
                time.sleep(1)

                # Clear any stale data from buffer
                #self.serial.flushInput()

                #self.serial.write(b'hello')
                answer = self.read_Data()
                if answer != "":
                    self.desc.setText(self.desc.toPlainText() + "Connected!\n" + answer)
            except SerialException as e:
                    self.desc.setText("\nNo hay ningun puerto reconocido o seleccionado... revisar si se tiene el puerto\
                    en el IDE de ARDUINO abierto\n")

        elif self.desc.toPlainText() != ">> Ready to reconnect\n":
            print(self.desc.toPlainText())
            self.desc.setText(">> {} already Opened!\n".format(self.typeBox.currentText()) )
        else:
            self.desc.setText(">> Reconnecting to... {}\n".format(self.typeBox.currentText()))
            self.reconnect()

    def reconnect(self):
        self.serial.isOpen

        if self.serial.isOpen:
            self.serial.close()

            self.desc.setText("")
            self.desc.setText(">> trying to connect to port %s ..." % self.typeBox.currentText())
            try:
                self.serial = serial.Serial(self.typeBox.currentText(), 115200, timeout=1)
                time.sleep(1)

                # Clear any stale data from buffer
                # self.serial.flushInput()

                # self.serial.write(b'hello')
                answer = self.readData()
                if answer != "":
                    self.desc.setText(self.desc.toPlainText() + "Connected!\n" + answer)
            except SerialException as e:
                self.desc.setText("\nNo hay ningun puerto reconocido o seleccionado...\n")

    def parseCommand(self, command):
        #En esta funcion se analizará el comando de entrada que nos llego desde el ESP32, con el que podremos
        #Alzar una bandera y determinar si se trata de un comando en especifico para leer continuamente o no
        if command == "start_measure":
            start_measurements_state = True #Queremos que se lea continuamente el puerto serial ya que la informacion
            #que llegara es de suma importancia para la graficación
            command_parsed = True
            readThread.start()
        elif command == "step_motor":
            step_motor_state = True #Con este solo sabremos que el motor se movio una cierta cantidad pero no necesitamos
            #lectura continua
            command_parsed = True # con esta bandera sabremos si se analizo el comando y luego de realizada la accion se baja de nuevo para



    def read_Data(self):
        global outListx
        global outListy
        global start_measurements_state # Con esta variable controlaremos si estamos en el modo de lectura continua de datos

        # Iniciamos la comunicación serial con el COM y el BAUDRATE

        time.sleep(0.3)  # Dejamos un tiempo de demora de 1 segundo
        self.serial.flush()  # it is buffering. required to get the data out *now*
        answer = ""
        while self.serial.inWaiting() > 0:
            if start_measurements_state:

                answer = str(self.serial.readline().decode('utf-8'))

                char_t = answer.decode('ascii')  # Decodificamos cada linea
                # print(char_t)
                try:
                    # print(char_t)
                    # outList.append(int(char_t[1:-1]))
                    # char_t = char_t[1:-1]
                    char_t = char_t.split(" ")
                    char_t[1] = char_t[1][:-2]

                    char_t[0] = float(char_t[0])
                    char_t[1] = float(char_t[1])
                    outListx.append(char_t[1])
                    outListy.append(char_t[0])
                except:
                    continue

            else:
                answer = str(self.serial.readline().decode('utf-8'))

        command_to_analize = answer.replace("\\r", "").replace("\\n", "").replace("'", "")

        answer = "\n" + answer.replace("\\r", "").replace("\\n", "").\
                replace("'", "")



        ## Analizador de comandos
        if not command_parsed and '@' in self.title.text():
            ## Aqui analizaremos el comando
            self.parseCommand(command_to_analize)

        return answer

    def sendData(self):
        try:
            if self.serial.isOpen():
                if self.title.text() != "":
                    self.serial.write(self.title.text().encode())
                    time.sleep(0.2)
                    answer = self.read_Data()
                    self.desc.setText(self.desc.toPlainText() + "\n" + answer)
        except AttributeError:
            self.desc.setText("\nTratando de enviar dato sin puerto activado...\n")

    def init(self):
        self.setTitle(self.title)

        self.selectlbl = QLabel("Select port:")
        # label
        self.typeBox = QComboBox()
        self.typeBox.addItems(self.items)  # database getMotionType()
        self.typeBox.setCurrentIndex(self.typeBox.count() - 1)

        # btn
        button = QPushButton("Connect")
        button.clicked.connect(self.connect)
        sendBtn = QPushButton("Send")
        sendBtn.clicked.connect(self.sendData)

        titlelbl = QLabel("Enter")
        self.title = QLineEdit("")
        desclbl = QLabel("Console")
        self.desc = QTextEdit("")

        self.fields = QGridLayout()
        self.fields.addWidget(self.selectlbl, 0, 0, 1, 1)
        self.fields.addWidget(self.typeBox, 0, 1, 1, 1)
        self.fields.addWidget(button, 0, 2, 1, 1)

        self.fields.addWidget(titlelbl, 1, 0, 1, 1)
        self.fields.addWidget(self.title, 1, 1, 1, 1)
        self.fields.addWidget(sendBtn, 1, 2, 1, 1)
        self.fields.addWidget(desclbl, 2, 0, 1, 1)
        self.fields.addWidget(self.desc, 3, 1, 1, 1)
        self.setLayout(self.fields)

        refreshBtn = QPushButton("Refresh")
        refreshBtn.clicked.connect(self.refreshPorts)
        self.fields.addWidget(refreshBtn, 0, 3, 1, 1)  # Adjust grid position as needed

        self.fields.addWidget(desclbl, 2, 0, 1, 1)
        self.fields.addWidget(self.desc, 3, 0, 1, 4)  # Adjust grid span to accommodate the new button
        self.setLayout(self.fields)

        clearBtn = QPushButton("Clear")
        clearBtn.clicked.connect(self.clearTypeBox)
        self.fields.addWidget(clearBtn, 1, 3, 1, 1)  # Adjust grid position as needed


if __name__ == "__main__":
    app = QApplication(sys.argv)
    frame = SerialInterface()
    frame.show()
    sys.exit(app.exec_())