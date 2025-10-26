import sys
import struct
import time
import os
from PyQt5.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot, QTimer, pyqtProperty, Qt
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QWidget, QMessageBox
from PyQt5.QtGui import QPixmap, QFont, QKeyEvent, QIntValidator, QIcon
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtSerialPort import QSerialPortInfo, QSerialPort
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Harita HTML dosyası oluştur
# (Leaflet ile iki marker ve çizgi)
def create_map_html():
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Roket Konumları</title>
    <meta charset=\"utf-8\">
    <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.7.1/dist/leaflet.css\" />
    <script src=\"https://unpkg.com/leaflet@1.7.1/dist/leaflet.js\"></script>
    <style>
        body { margin: 0; padding: 0; }
        #map { width: 100vw; height: 100vh; }
    </style>
</head>
<body>
    <div id=\"map\"></div>
    <script>
        var map = L.map('map').setView([39.9417, 32.86485], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        // Ana Sistem marker
        var anaSistem = L.marker([39.9334, 32.8597]).addTo(map);
        anaSistem.bindPopup('<b>Ana Sistem</b><br>39.9334°N, 32.8597°E');
        // Görev Yükü marker
        var gorevYuku = L.marker([39.9500, 32.8700]).addTo(map);
        gorevYuku.bindPopup('<b>Görev Yükü</b><br>39.9500°N, 32.8700°E');
        // Tüm markerları göster
        var group = new L.featureGroup([anaSistem, gorevYuku]);
        map.fitBounds(group.getBounds().pad(0.3));
    </script>
</body>
</html>
"""
    with open("map.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    return os.path.abspath("map.html")

QML_CODE = '''
import QtQuick 2.15
import QtQuick.Controls 1.4
import QtQuick.Controls 2.15 as QQC2
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import QtWebEngine 1.8

ApplicationWindow {
    visible: true
    minimumWidth: 800
    minimumHeight: 600
    title: "111 - Roket Telemetri"
    flags: Qt.Window
    
    // Windows için renk teması
    property bool isWindows: Qt.platform.os === "windows"
    property string backgroundColor: isWindows ? "#2D2D30" : "#000000"
    property string borderColor: isWindows ? "#3F3F46" : "#FFFFFF"
    property string textColor: isWindows ? "#FFFFFF" : "#FFFFFF"
    property string accentColor: isWindows ? "#0078D4" : "#FFFFFF"
    property string secondaryColor: isWindows ? "#1E1E1E" : "#000000"
    
    property int selectedTeamId: 1
    property bool teamIdSet: false
    property bool teamIdLocked: false
    property string mapHtmlPath: ""
    property int judgeFreqHz: 5
    property real anaSistemLat: 39.9334
    property real anaSistemLon: 32.8597
    property real gorevYukuLat: 39.9500
    property real gorevYukuLon: 32.8700
    


            // Ana layout
        GridLayout {
            anchors.fill: parent
            anchors.margins: 15
            columns: 3
            rowSpacing: 15
            columnSpacing: 15
            

        
        // Takım Bilgisi (Sol üst)
        Rectangle {
            color: backgroundColor
            border.color: borderColor
            border.width: isWindows ? 1 : 3
            radius: isWindows ? 4 : 0
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 100
            Layout.columnSpan: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 5
                
                Text {
                    text: "TAKIM BILGISI"
                    font.capitalization: Font.AllUppercase
                    font.bold: true
                    font.pointSize: 12
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                    
                    RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    Text {
                        text: "Takım ID:"
                        font.bold: true
                        font.pointSize: 10
                        color: textColor
                    }
                    
                    TextField {
                        id: teamIdInput
                        text: "1"
                        Layout.preferredWidth: 60
                        Layout.preferredHeight: 25
                        horizontalAlignment: TextInput.AlignHCenter
                        validator: IntValidator {
                            bottom: 1
                            top: 255
                        }
                        enabled: !teamIdLocked
                        onTextChanged: {
                            if (serialManager && text !== "") {
                                var teamId = parseInt(text);
                                if (teamId >= 1 && teamId <= 255) {
                                    serialManager.set_team_id(teamId);
                                    teamIdDisplay.text = "Takım ID: " + teamId;
                                }
                            }
                        }
                    }
                    
                    Button {
                        text: teamIdLocked ? "Ayarla" : "Ayarlandı"
                        Layout.preferredWidth: 80
                        Layout.preferredHeight: 25
                        enabled: teamIdInput.text !== "" && parseInt(teamIdInput.text) >= 1 && parseInt(teamIdInput.text) <= 255
                        onClicked: {
                            if (!teamIdLocked) {
                                teamIdLocked = true;
                                teamIdInput.enabled = false;
                                console.log("[QML] Takım ID kilitlendi: " + teamIdInput.text);
                            }
                        }
                    }
                }
                
                Text {
                    id: teamIdDisplay
                    text: "Takım ID: 1"
                    font.bold: true
                    font.pointSize: 12
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: teamIdLocked ? "✅ Takım ID kilitlendi" : "⚠️ Hakem bağlantısından önce kilitleyin"
                    font.pointSize: 8
                    color: teamIdLocked ? "#00FF00" : "#FFAA00"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
        
        // Bağlantı Durumu (Orta üst)
        Rectangle {
            color: backgroundColor
            border.color: borderColor
            border.width: isWindows ? 1 : 2
            radius: isWindows ? 4 : 0
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 100
            Layout.columnSpan: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 5
                
                Text {
                    text: "BAĞLANTI DURUMU"
                    font.capitalization: Font.AllUppercase
                    font.bold: true
                    font.pointSize: 12
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    id: telemetryStatusText
                    text: "Telemetri: ❌ Bağlı Değil"
                    font.bold: true
                    font.pointSize: 10
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    id: telemetry2StatusText
                    text: "Telemetri2: ❌ Bağlı Değil"
                    font.bold: true
                    font.pointSize: 10
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    id: judgeStatusText
                    text: "Hakem: ❌ Bağlı Değil"
                    font.bold: true
                    font.pointSize: 10
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
        
        // Harita Konum (Sağ üst)
        Rectangle {
            color: backgroundColor
            border.color: borderColor
            border.width: isWindows ? 1 : 2
            radius: isWindows ? 4 : 0
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 100
            Layout.columnSpan: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 5
                
                Text {
                    text: "HARITA KONUM"
                    font.capitalization: Font.AllUppercase
                    font.bold: true
                    font.pointSize: 12
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    // Hz ayarlama paneli arayüzden kaldırıldı
                }
                
                Text {
                    id: anaSistemKoordinat
                    text: "Ana Sistem: 0°N, 0°E"
                    font.pointSize: 8
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    id: gorevYukuKoordinat
                    text: "Görev Yükü: 0°N, 0°E"
                    font.pointSize: 8
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                

                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    Button {
                        text: "📍 Ana Sistem"
                        Layout.fillWidth: true
                        height: 25
                        onClicked: {
                            var mapUrl = "https://www.openstreetmap.org/?mlat=" + anaSistemLat + "&mlon=" + anaSistemLon + "&zoom=13&layers=M";
                            Qt.openUrlExternally(mapUrl);
                        }
                    }
                    
                    Button {
                        text: "📍 Görev Yükü"
                        Layout.fillWidth: true
                        height: 25
                        onClicked: {
                            var mapUrl = "https://www.openstreetmap.org/?mlat=" + gorevYukuLat + "&mlon=" + gorevYukuLon + "&zoom=13&layers=M";
                            Qt.openUrlExternally(mapUrl);
                        }
                    }
                }
            }
        }

        // Telemetri Portu (Sol alt)
        Rectangle {
            color: backgroundColor
            border.color: borderColor
            border.width: isWindows ? 1 : 2
            radius: isWindows ? 4 : 0
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 200
            Layout.columnSpan: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                
                Text {
                    text: "TELEMETRI PORTU"
                    font.capitalization: Font.AllUppercase
                    font.bold: true
                    font.pointSize: 12
                    color: textColor
                    Layout.alignment: Qt.AlignHCenter
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    Text {
                        text: "Baudrate:"
                        font.bold: true
                        font.pointSize: 10
                        color: "#FFFFFF"
                    }
                    
                    ComboBox {
                        id: telemetryBaudCombo
                        Layout.fillWidth: true
                        model: ["9600", "19200", "38400", "57600", "115200"]
                        currentIndex: 1
                    }
                }
                

                
                // Port tarama butonu
                Button {
                    text: "🔍 Portları Tara"
                    Layout.fillWidth: true
                    height: 25
                    onClicked: {
                        if (serialManager) {
                            console.log("[QML] Telemetri portları taranıyor...");
                            var ports = serialManager.scan_ports();
                            telemetryPortModel.clear();
                            if (ports.length === 0) {
                                telemetryPortModel.append({name: "Port yok", path: ""});
                                console.log("[QML] Telemetri portu bulunamadı");
                            } else {
                                for (var i = 0; i < ports.length; ++i) {
                                    telemetryPortModel.append(ports[i]);
                                    console.log("[QML] Telemetri portu eklendi:", ports[i].name);
                                }
                            }
                        }
                    }
                }
                
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    
                    Rectangle {
                        anchors.fill: parent
                        color: "#000000"
                        border.color: "#000000"
                        border.width: 2
                    }
                    
                    ComboBox {
                        id: telemetryCombo
                        anchors.fill: parent
                        anchors.margins: 5
                        model: ListModel { id: telemetryPortModel }
                        textRole: "name"
                        currentIndex: 0
                    }
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    Button {
                        id: telemetryConnectBtn
                        text: "Bağlan"
                        Layout.fillWidth: true
                        height: 25
                        enabled: telemetryPortModel.count > 0
                        onClicked: {
                            if (serialManager && telemetryPortModel.count > 0 && telemetryCombo.currentIndex >= 0) {
                                var portPath = telemetryPortModel.get(telemetryCombo.currentIndex).path;
                                var baud = parseInt(telemetryBaudCombo.currentText);
                                var success = serialManager.connect_telemetry(portPath, baud);
                                if (success) {
                                    telemetryStatusText.text = "Telemetri: ✅ Bağlı (" + portPath + ")";
                                }
                            }
                        }
                    }
                    Button {
                        id: telemetryDisconnectBtn
                        text: "Bağlantıyı Kes"
                        Layout.fillWidth: true
                        height: 25
                        enabled: telemetryPortModel.count > 0
                        onClicked: {
                            if (serialManager) {
                                serialManager.disconnect_telemetry();
                                telemetryStatusText.text = "Telemetri: ❌ Bağlı Değil";
                            }
                        }
                    }
                }
            }
        }
        
        // Telemetri2 Portu (Orta alt)
        Rectangle {
            color: "#000000"
            border.color: "#FFFFFF"
            border.width: 2
            radius: 0
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 200
            Layout.columnSpan: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                
                Text {
                    text: "TELEMETRI2 PORTU"
                    font.capitalization: Font.AllUppercase
                    font.bold: true
                    font.pointSize: 12
                    color: "#FFFFFF"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    Text {
                        text: "Baudrate:"
                        font.bold: true
                        font.pointSize: 10
                        color: "#FFFFFF"
                    }
                    
                    ComboBox {
                        id: telemetry2BaudCombo
                        Layout.fillWidth: true
                        model: ["9600", "19200", "38400", "57600", "115200"]
                        currentIndex: 1
                    }
                }
                

                
                // Port tarama butonu
                Button {
                    text: "🔍 Portları Tara"
                    Layout.fillWidth: true
                    height: 25
                    onClicked: {
                        if (serialManager) {
                            console.log("[QML] Telemetri2 portları taranıyor...");
                            var ports = serialManager.scan_ports();
                            telemetry2PortModel.clear();
                            if (ports.length === 0) {
                                telemetry2PortModel.append({name: "Port yok", path: ""});
                                console.log("[QML] Telemetri2 portu bulunamadı");
                            } else {
                                for (var i = 0; i < ports.length; ++i) {
                                    telemetry2PortModel.append(ports[i]);
                                    console.log("[QML] Telemetri2 portu eklendi:", ports[i].name);
                                }
                            }
                        }
                    }
                }
                
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    
                    Rectangle {
                        anchors.fill: parent
                        color: "#000000"
                        border.color: "#000000"
                        border.width: 2
                    }
                    
                    ComboBox {
                        id: telemetry2Combo
                        anchors.fill: parent
                        anchors.margins: 5
                        model: ListModel { id: telemetry2PortModel }
                        textRole: "name"
                        currentIndex: 0
                    }
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    Button {
                        id: telemetry2ConnectBtn
                        text: "Bağlan"
                        Layout.fillWidth: true
                        height: 25
                        enabled: telemetry2PortModel.count > 0
                        onClicked: {
                            if (serialManager && telemetry2PortModel.count > 0 && telemetry2Combo.currentIndex >= 0) {
                                var portPath = telemetry2PortModel.get(telemetry2Combo.currentIndex).path;
                                var baud = parseInt(telemetry2BaudCombo.currentText);
                                var success = serialManager.connect_telemetry2(portPath, baud);
                                if (success) {
                                    telemetry2StatusText.text = "Telemetri2: ✅ Bağlı (" + portPath + ")";
                                }
                            }
                        }
                    }
                    Button {
                        id: telemetry2DisconnectBtn
                        text: "Bağlantıyı Kes"
                        Layout.fillWidth: true
                        height: 25
                        enabled: telemetry2PortModel.count > 0
                        onClicked: {
                            if (serialManager) {
                                serialManager.disconnect_telemetry2();
                                telemetry2StatusText.text = "Telemetri2: ❌ Bağlı Değil";
                            }
                        }
                    }
                }
            }
        }
        
        // Hakem Portu (Sağ alt)
        Rectangle {
            color: "#000000"
            border.color: "#FFFFFF"
            border.width: 2
            radius: 0
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 200
            Layout.columnSpan: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                
                Text {
                    text: "HAKEM PORTU"
                    font.capitalization: Font.AllUppercase
                    font.bold: true
                    font.pointSize: 12
                    color: "#FFFFFF"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    Text {
                        text: "Baudrate:"
                        font.bold: true
                        font.pointSize: 10
                        color: "#FFFFFF"
                    }
                    
                    ComboBox {
                        id: judgeBaudCombo
                        Layout.fillWidth: true
                        model: ["9600", "19200", "38400", "57600", "115200"]
                        currentIndex: 1
                    }
                }
                

                
                // Port tarama butonu
                Button {
                    text: "🔍 Portları Tara"
                    Layout.fillWidth: true
                    height: 25
                    onClicked: {
                        if (serialManager) {
                            console.log("[QML] Hakem portları taranıyor...");
                            var ports = serialManager.scan_ports();
                            judgePortModel.clear();
                            if (ports.length === 0) {
                                judgePortModel.append({name: "Port yok", path: ""});
                                console.log("[QML] Hakem portu bulunamadı");
                            } else {
                                for (var i = 0; i < ports.length; ++i) {
                                    judgePortModel.append(ports[i]);
                                    console.log("[QML] Hakem portu eklendi:", ports[i].name);
                                }
                            }
                        }
                    }
                }
                
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    
                    Rectangle {
                        anchors.fill: parent
                        color: "#000000"
                        border.color: "#000000"
                        border.width: 2
                    }
                    
                    ComboBox {
                        id: judgeCombo
                        anchors.fill: parent
                        anchors.margins: 5
                        model: ListModel { id: judgePortModel }
                        textRole: "name"
                        currentIndex: 0
                    }
                }
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    
                    Button {
                        id: judgeConnectBtn
                        text: "Bağlan"
                        Layout.fillWidth: true
                        height: 25
                        enabled: judgePortModel.count > 0 && teamIdLocked
                        onClicked: {
                            if (!teamIdLocked) {
                                console.log("[QML] ❌ Takım ID kilitlenmeden hakem bağlantısı kurulamaz!");
                                return;
                            }
                            if (serialManager && judgePortModel.count > 0 && judgeCombo.currentIndex >= 0) {
                                var portPath = judgePortModel.get(judgeCombo.currentIndex).path;
                                var baud = parseInt(judgeBaudCombo.currentText);
                                var success = serialManager.connect_judge(portPath, baud);
                                if (success) {
                                    judgeStatusText.text = "Hakem: ✅ Bağlı (" + portPath + ")";
                                }
                            }
                        }
                    }
                    Button {
                        id: judgeDisconnectBtn
                        text: "Bağlantıyı Kes"
                        Layout.fillWidth: true
                        height: 25
                        enabled: judgePortModel.count > 0
                        onClicked: {
                            if (serialManager) {
                                serialManager.disconnect_judge();
                                judgeStatusText.text = "Hakem: ❌ Bağlı Değil";
                            }
                        }
                    }
                }
            }
        }
        

        
        // Telemetri Verileri (Alt kısım - tam genişlik)
        Rectangle {
            color: "#000000"
            border.color: "#FFFFFF"
            border.width: 2
            radius: 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.columnSpan: 3
            Layout.preferredHeight: 300
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                
                Text {
                    text: "TELEMETRI VERILERI"
                    font.capitalization: Font.AllUppercase
                    font.bold: true
                    font.pointSize: 12
                    color: "#FFFFFF"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                TableView {
                    id: telemetryTable
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: ListModel {
                        id: telemetryModel
                        ListElement { field: "Takım ID"; value: "-" }
                        ListElement { field: "Paket Sayacı"; value: "-" }
                        ListElement { field: "Durum"; value: "-" }
                        ListElement { field: "Açı"; value: "-" }
                        ListElement { field: "İrtifa"; value: "-" }
                        ListElement { field: "Roket GPS İrtifa"; value: "-" }
                        ListElement { field: "Roket Enlem"; value: "-" }
                        ListElement { field: "Roket Boylam"; value: "-" }
                        ListElement { field: "Görev Yükü GPS İrtifa"; value: "-" }
                        ListElement { field: "Görev Yükü Enlem"; value: "-" }
                        ListElement { field: "Görev Yükü Boylam"; value: "-" }
                        ListElement { field: "Jiroskop X"; value: "-" }
                        ListElement { field: "Jiroskop Y"; value: "-" }
                        ListElement { field: "Jiroskop Z"; value: "-" }
                        ListElement { field: "Ana Sistem İvme X"; value: "-" }
                        ListElement { field: "Ana Sistem İvme Y"; value: "-" }
                        ListElement { field: "Ana Sistem İvme Z"; value: "-" }
                                        ListElement { field: "RMS Internal"; value: "-" }
                ListElement { field: "RMS External"; value: "-" }
                    }
                    
                    TableViewColumn {
                        title: "Alan"
                        role: "field"
                        width: 200
                    }
                    TableViewColumn {
                        title: "Değer"
                        role: "value"
                        width: 150
                    }
                }
            }
        }
    }

    Connections {
        target: serialManager
        function onTelemetryConnectedChanged() {
            if (serialManager) {
                if (serialManager.telemetryConnected) {
                    telemetryStatusText.text = "Telemetri: ✅ Bağlı (" + serialManager.telemetryPortName + ")";
                } else {
                    telemetryStatusText.text = "Telemetri: ❌ Bağlı Değil";
                }
            }
        }
        function onTelemetry2ConnectedChanged() {
            if (serialManager) {
                if (serialManager.telemetry2Connected) {
                    telemetry2StatusText.text = "Telemetri2: ✅ Bağlı (" + serialManager.telemetry2PortName + ")";
                } else {
                    telemetry2StatusText.text = "Telemetri2: ❌ Bağlı Değil";
                }
            }
        }
        function onJudgeConnectedChanged() {
            if (serialManager) {
                if (serialManager.judgeConnected) {
                    judgeStatusText.text = "Hakem: ✅ Bağlı (" + serialManager.judgePortName + ")";
                    // Hakem bağlandığında frekansı ayarla
                    serialManager.set_judge_send_frequency(judgeFreqHz);
                } else {
                    judgeStatusText.text = "Hakem: ❌ Bağlı Değil";
                }
            }
        }
        function onTelemetry_data_changed() {
            if (serialManager && serialManager.telemetry_data_property) {
                var data = serialManager.telemetry_data_property;
                if (data.fields) {
                    for (var i = 0; i < telemetryModel.count; ++i) {
                        var fieldName = telemetryModel.get(i).field;
                        var value = data.fields[fieldName];
                        if (value !== undefined && value !== null) {
                            telemetryModel.setProperty(i, "value", value);
                        }
                    }
                    
                    // Harita koordinatlarını güncelle
                    updateMapCoordinates(data.fields);
                }
            }
        }
        
        function updateMapCoordinates(fields) {
            // Ana sistem koordinatları
            var rocketLat = fields["Roket Enlem"];
            var rocketLon = fields["Roket Boylam"];
            if (rocketLat && rocketLon) {
                var lat = parseFloat(rocketLat.replace("°", ""));
                var lon = parseFloat(rocketLon.replace("°", ""));
                if (!isNaN(lat) && !isNaN(lon)) {
                    anaSistemLat = lat;
                    anaSistemLon = lon;
                    anaSistemKoordinat.text = "Ana Sistem: " + lat.toFixed(6) + "°N, " + lon.toFixed(6) + "°E";
                }
            }
            
            // Görev yükü koordinatları
            var payloadLat = fields["Görev Yükü Enlem"];
            var payloadLon = fields["Görev Yükü Boylam"];
            if (payloadLat && payloadLon) {
                var lat = parseFloat(payloadLat.replace("°", ""));
                var lon = parseFloat(payloadLon.replace("°", ""));
                if (!isNaN(lat) && !isNaN(lon)) {
                    gorevYukuLat = lat;
                    gorevYukuLon = lon;
                    gorevYukuKoordinat.text = "Görev Yükü: " + lat.toFixed(6) + "°N, " + lon.toFixed(6) + "°E";
                }
            }
        }
        function onPortsChanged(ports) {
            // Telemetri port modelini güncelle
            telemetryPortModel.clear();
            if (ports.length === 0) {
                telemetryPortModel.append({name: "Port yok", path: ""});
            } else {
                for (var i = 0; i < ports.length; ++i) {
                    telemetryPortModel.append(ports[i]);
                }
            }
            
            // Telemetri2 port modelini güncelle
            telemetry2PortModel.clear();
            if (ports.length === 0) {
                telemetry2PortModel.append({name: "Port yok", path: ""});
            } else {
                for (var i = 0; i < ports.length; ++i) {
                    telemetry2PortModel.append(ports[i]);
                }
            }
            
            // Hakem port modelini güncelle
            judgePortModel.clear();
            if (ports.length === 0) {
                judgePortModel.append({name: "Port yok", path: ""});
            } else {
                for (var i = 0; i < ports.length; ++i) {
                    judgePortModel.append(ports[i]);
                }
            }
            
            console.log("[QML] Port listeleri güncellendi");
        }
    }
    
    Component.onCompleted: {
        // Başlangıçta bağlantı durumunu kontrol et
        if (serialManager) {
            mapHtmlPath = serialManager.map_html_path || "";
            if (serialManager.telemetryConnected) {
                telemetryStatusText.text = "Telemetri: ✅ Bağlı (" + (serialManager.telemetryPortName || "") + ")";
            }
            if (serialManager.telemetry2Connected) {
                telemetry2StatusText.text = "Telemetri2: ✅ Bağlı (" + (serialManager.telemetry2PortName || "") + ")";
            }
            if (serialManager.judgeConnected) {
                judgeStatusText.text = "Hakem: ✅ Bağlı (" + (serialManager.judgePortName || "") + ")";
            }
            
            // Takım ID'yi göster
            var teamId = serialManager.get_team_id();
            teamIdDisplay.text = "Takım ID: " + teamId;
            teamIdInput.text = teamId.toString();
            
            // Başlangıçta port listelerini boş olarak ayarla
            telemetryPortModel.clear();
            telemetryPortModel.append({name: "Port taranmadı", path: ""});
            telemetry2PortModel.clear();
            telemetry2PortModel.append({name: "Port taranmadı", path: ""});
            judgePortModel.clear();
            judgePortModel.append({name: "Port taranmadı", path: ""});
            
            // Başlangıçta hakem frekansını ayarla
            serialManager.set_judge_send_frequency(judgeFreqHz);
        }
    }
}
'''

class SerialManager(QObject):
    # Signals
    telemetry_data_changed = pyqtSignal()
    telemetry_ports_changed = pyqtSignal()
    telemetryConnectedChanged = pyqtSignal()
    telemetry2ConnectedChanged = pyqtSignal()
    judgeConnectedChanged = pyqtSignal()
    telemetry_status_changed = pyqtSignal()
    telemetry2_status_changed = pyqtSignal()
    judge_status_changed = pyqtSignal()
    portsChanged = pyqtSignal(list)  # QML için portsChanged sinyali
    
    def __init__(self):
        super().__init__()
        self.telemetry_port = None  # Ana sistem
        self.telemetry2_port = None  # Görev yükü
        self.judge_port = None  # Hakem
        self._telemetry_connected = False
        self._telemetry2_connected = False
        self._judge_connected = False
        self._telemetry_port_name = ""
        self._telemetry2_port_name = ""
        self._judge_port_name = ""
        self.team_id = 1
        self.telemetry_data = {'fields': {}}
        self.angle = 0.0
        self.map_html_path = ""
        self.packet_counter = 0
        
        # Veri birleştirme sistemi için değişkenler
        self.ana_sistem_data = {}  # Ana sistem verilerini sakla
        self.gorev_yuku_data = {}  # Görev yükü verilerini sakla
        self.judge_timer = None  # Hakem gönderme timer'ı
        self.judge_send_interval = 200  # 200ms = 5Hz (saniyede 5 kere)
        

        
        # Harita dosyasını oluştur
        self.map_html_path = create_map_html()
        
        # Hakem gönderme timer'ını başlat
        self._start_judge_timer()
    
    def _start_judge_timer(self):
        """Hakem gönderme timer'ını başlatır"""
        if self.judge_timer is None:
            self.judge_timer = QTimer()
            self.judge_timer.timeout.connect(self._send_combined_data_to_judge)
            self.judge_timer.start(self.judge_send_interval)
            print(f"[PYTHON] ✅ Hakem gönderme timer başlatıldı ({self.judge_send_interval}ms = {1000//self.judge_send_interval}Hz)")
    
    @pyqtSlot(int)
    def set_judge_send_frequency(self, frequency_hz):
        """Hakem gönderme frekansını ayarlar (Hz cinsinden)"""
        if frequency_hz < 1 or frequency_hz > 10:  # 1-10 Hz arası sınırla
            print(f"[PYTHON] ❌ Geçersiz frekans: {frequency_hz}Hz (1-10 Hz arası olmalı)")
            return
        
        self.judge_send_interval = 1000 // frequency_hz  # Hz'i ms'e çevir
        if self.judge_timer and self.judge_timer.isActive():
            self.judge_timer.setInterval(self.judge_send_interval)
            print(f"[PYTHON] ✅ Hakem gönderme frekansı güncellendi: {frequency_hz}Hz ({self.judge_send_interval}ms)")
        else:
            print(f"[PYTHON] ⚠️ Timer aktif değil, frekans ayarlandı: {frequency_hz}Hz")
    
    @pyqtSlot(result=int)
    def get_judge_send_frequency(self):
        """Mevcut hakem gönderme frekansını döndürür (Hz cinsinden)"""
        return 1000 // self.judge_send_interval
    
    def _send_combined_data_to_judge(self):
        """Birleştirilmiş verileri hakeme gönderir"""
        try:
            if not self.judge_port or not self.judge_port.isOpen():
                return
                
            # Paket sayacını artır
            self.packet_counter = (self.packet_counter + 1) % 256
            
            # Ana sistem verilerini al (varsayılan değerler)
            ana_altitude = self.ana_sistem_data.get('altitude', 0.0)
            ana_gps_altitude = self.ana_sistem_data.get('gps_altitude', 0.0)
            ana_latitude = self.ana_sistem_data.get('latitude', 0.0)
            ana_longitude = self.ana_sistem_data.get('longitude', 0.0)
            ana_gyro_x = self.ana_sistem_data.get('gyro_x', 0.0)
            ana_gyro_y = self.ana_sistem_data.get('gyro_y', 0.0)
            ana_gyro_z = self.ana_sistem_data.get('gyro_z', 0.0)
            ana_acc_x = self.ana_sistem_data.get('acc_x', 0.0)
            ana_acc_y = self.ana_sistem_data.get('acc_y', 0.0)
            ana_acc_z = self.ana_sistem_data.get('acc_z', 0.0)
            ana_angle = self.ana_sistem_data.get('angle', 0.0)
            ana_status = self.ana_sistem_data.get('status', 0)
            
            # Görev yükü verilerini al (varsayılan değerler)
            gorev_altitude = self.gorev_yuku_data.get('altitude', 0.0)
            gorev_gps_altitude = self.gorev_yuku_data.get('gps_altitude', 0.0)
            gorev_latitude = self.gorev_yuku_data.get('latitude', 0.0)
            gorev_longitude = self.gorev_yuku_data.get('longitude', 0.0)
            
            # Kademe verileri için 0 değerleri (kademe yok)
            stage_gps_altitude = 0.0
            stage_latitude = 0.0
            stage_longitude = 0.0
            
            # HYI paketi oluştur - Birleştirilmiş veriler
            packet = self.create_hyi_packet(
                self.packet_counter,
                ana_altitude,  # Ana paket irtifa (ana sistem)
                ana_gps_altitude,  # Roket GPS İrtifa (ana sistem)
                ana_latitude,  # Roket Enlem (ana sistem)
                ana_longitude,  # Roket Boylam (ana sistem)
                gorev_gps_altitude,  # Görev Yükü GPS İrtifa (görev yükü)
                gorev_latitude,  # Görev Yükü Enlem (görev yükü)
                gorev_longitude,  # Görev Yükü Boylam (görev yükü)
                stage_gps_altitude,  # Kademe GPS İrtifa (0)
                stage_latitude,  # Kademe Enlem (0)
                stage_longitude,  # Kademe Boylam (0)
                ana_gyro_x,  # Jiroskop X (ana sistem)
                ana_gyro_y,  # Jiroskop Y (ana sistem)
                ana_gyro_z,  # Jiroskop Z (ana sistem)
                ana_acc_x,  # İvme X (ana sistem)
                ana_acc_y,  # İvme Y (ana sistem)
                ana_acc_z,  # İvme Z (ana sistem)
                ana_angle,  # Açı (ana sistem)
                ana_status  # Durum (ana sistem)
            )
            
            # Paketi hakem portuna gönder
            self.judge_port.write(packet)
            print(f"[PYTHON] Hakem yer istasyonuna birleştirilmiş veri gönderildi (Paket: {self.packet_counter})")
            print(f"[PYTHON] Ana Sistem: Alt={ana_altitude}, GPS={ana_gps_altitude}, Lat={ana_latitude}, Lng={ana_longitude}")
            print(f"[PYTHON] Görev Yükü: Alt={gorev_altitude}, GPS={gorev_gps_altitude}, Lat={gorev_latitude}, Lng={gorev_longitude}")
            
        except Exception as e:
            print(f"[PYTHON] Hakem birleştirilmiş veri gönderme hatası: {e}")

    @pyqtProperty(bool, notify=telemetryConnectedChanged)
    def telemetry_connected(self):
        return self._telemetry_connected
    
    @pyqtProperty(bool, notify=telemetry2ConnectedChanged)
    def telemetry2_connected(self):
        return self._telemetry2_connected
    
    @pyqtProperty(str, notify=telemetry_status_changed)
    def telemetry_status(self):
        if self._telemetry_connected:
            return f"Bağlı ({self._telemetry_port_name})"
        return "Bağlı Değil"
    
    @pyqtProperty(str, notify=telemetry2_status_changed)
    def telemetry2_status(self):
        if self._telemetry2_connected:
            return f"Bağlı ({self._telemetry2_port_name})"
        return "Bağlı Değil"

    @pyqtProperty(str, notify=telemetry_ports_changed)
    def telemetry_port_name(self):
        return self._telemetry_port_name
    
    @pyqtProperty(str, notify=telemetry_ports_changed)
    def telemetry2_port_name(self):
        return self._telemetry2_port_name

    @pyqtProperty(bool, notify=judgeConnectedChanged)
    def judge_connected(self):
        return self._judge_connected
    
    @pyqtProperty(str, notify=judge_status_changed)
    def judge_status(self):
        if self._judge_connected:
            return f"Bağlı ({self._judge_port_name})"
        return "Bağlı Değil"

    @pyqtProperty(str, notify=telemetry_ports_changed)
    def judge_port_name(self):
        return self._judge_port_name

    @pyqtSlot(int)
    def set_team_id(self, team_id):
        self.team_id = team_id
        print(f"[PYTHON] Takım ID ayarlandı: {team_id}")

    @pyqtSlot(result=int)
    def get_team_id(self):
        return self.team_id

    @pyqtSlot(result=list)
    def scan_ports(self):
        print("[PYTHON] 🔍 Port tarama başlatıldı...")
        filtered_ports = []
        
        if sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
            # macOS ve Linux için
            try:
                for dev in os.listdir('/dev'):
                    if (dev.startswith('ttyUSB') or dev.startswith('ttyACM') or 
                        dev.startswith('cu.usbserial') or dev.startswith('cu.usbmodem')):
                        path = '/dev/' + dev
                        try:
                            ser = QSerialPort(path)
                            ser.setBaudRate(19200)
                            if ser.open(QSerialPort.ReadWrite):
                                filtered_ports.append({'name': dev, 'path': path})
                                ser.close()
                        except Exception as e:
                            pass
            except Exception as e:
                pass
        else:
            # Windows için
            try:
                ports = QSerialPortInfo.availablePorts()
                for port_info in ports:
                    port_name = port_info.portName()
                    # Windows'ta COM portları
                    if port_name.startswith('COM'):
                        try:
                            ser = QSerialPort(port_name)
                            ser.setBaudRate(19200)
                            if ser.open(QSerialPort.ReadWrite):
                                # Windows'ta port adını daha açıklayıcı yap
                                display_name = f"COM Port ({port_name})"
                                if port_info.description():
                                    display_name = f"{port_name} - {port_info.description()}"
                                filtered_ports.append({'name': display_name, 'path': port_name})
                                ser.close()
                        except Exception as e:
                            # Port kullanımda olabilir, yine de listeye ekle
                            display_name = f"{port_name} (Kullanımda)"
                            filtered_ports.append({'name': display_name, 'path': port_name})
            except Exception as e:
                print(f"[PYTHON] Windows port tarama hatası: {e}")
        
        print(f"[PYTHON] ✅ Toplam {len(filtered_ports)} seri port bulundu")
        self.ports = filtered_ports
        self.telemetry_ports_changed.emit()
        self.portsChanged.emit(filtered_ports)  # QML için sinyal gönder
        return filtered_ports

    def float_to_bytes(self, f):
        """FLOAT32 değerini 4 byte'lık bir bayt dizisine dönüştürür."""
        return struct.pack('<f', f)

    def create_hyi_packet(self, packet_counter, altitude, rocket_gps_altitude,
                          rocket_latitude, rocket_longitude, payload_gps_altitude,
                          payload_latitude, payload_longitude, stage_gps_altitude,
                          stage_latitude, stage_longitude, gyroscope_x, gyroscope_y,
                          gyroscope_z, acceleration_x, acceleration_y, acceleration_z,
                          angle, status):
        """HYİ haberleşme protokolüne uygun 78 byte'lık bir paket oluşturur."""
        packet = bytearray(78)

        # Sabit başlık ve kuyruk değerleri
        packet[0] = 0xFF
        packet[1] = 0xFF
        packet[2] = 0x54
        packet[3] = 0x52

        # Takım ID (UINT8) - self.team_id kullan
        packet[4] = self.team_id & 0xFF

        # Paket Sayacı (UINT8)
        packet[5] = packet_counter & 0xFF

        # FLOAT32 değerleri için byte dönüşümü ve atama
        # İrtifa
        _bytes = self.float_to_bytes(altitude)
        packet[6:10] = _bytes

        # Roket GPS İrtifa
        _bytes = self.float_to_bytes(rocket_gps_altitude)
        packet[10:14] = _bytes

        # Roket Enlem
        _bytes = self.float_to_bytes(rocket_latitude)
        packet[14:18] = _bytes

        # Roket Boylam
        _bytes = self.float_to_bytes(rocket_longitude)
        packet[18:22] = _bytes

        # Görev Yükü GPS İrtifa
        _bytes = self.float_to_bytes(payload_gps_altitude)
        packet[22:26] = _bytes

        # Görev Yükü Enlem
        _bytes = self.float_to_bytes(payload_latitude)
        packet[26:30] = _bytes

        # Görev Yükü Boylam
        _bytes = self.float_to_bytes(payload_longitude)
        packet[30:34] = _bytes

        # Kademe GPS İrtifa
        _bytes = self.float_to_bytes(stage_gps_altitude)
        packet[34:38] = _bytes

        # Kademe Enlem
        _bytes = self.float_to_bytes(stage_latitude)
        packet[38:42] = _bytes

        # Kademe Boylam
        _bytes = self.float_to_bytes(stage_longitude)
        packet[42:46] = _bytes

        # Jiroskop X
        _bytes = self.float_to_bytes(gyroscope_x)
        packet[46:50] = _bytes

        # Jiroskop Y
        _bytes = self.float_to_bytes(gyroscope_y)
        packet[50:54] = _bytes

        # Jiroskop Z
        _bytes = self.float_to_bytes(gyroscope_z)
        packet[54:58] = _bytes

        # İvme X
        _bytes = self.float_to_bytes(acceleration_x)
        packet[58:62] = _bytes

        # İvme Y
        _bytes = self.float_to_bytes(acceleration_y)
        packet[62:66] = _bytes

        # İvme Z
        _bytes = self.float_to_bytes(acceleration_z)
        packet[66:70] = _bytes

        # Açı
        _bytes = self.float_to_bytes(angle)
        packet[70:74] = _bytes

        # Durum (UINT8)
        packet[74] = status & 0xFF

        # Checksum Hesaplama
        checksum = sum(packet[4:75]) % 256
        packet[75] = checksum

        # Sabit kuyruk değerleri
        packet[76] = 0x0D
        packet[77] = 0x0A

        return packet

    def parse_telemetry_packet(self, packet_data):
        """JSON formatında gelen telemetri verisini parse eder"""
        try:
            import json
            data = json.loads(packet_data)
            
            # Ana sistem formatı kontrolü (alt, accX, accY, accZ alanları varsa)
            if 'header' in data and data.get('header') == 82 and 'rms_internal' in data and 'rms_external' in data:
                kaynak = 'gorev_yuku'
            elif 'alt' in data or 'accX' in data or 'accY' in data or 'accZ' in data:
                kaynak = 'anakart'
            else:
                kaynak = 'gorev_yuku'
            
            # Gelen JSON verilerini al (ana sistem formatı)
            if kaynak == 'anakart':
                irtifa = data.get('alt', 0.0)
                gps_irtifa = data.get('gpsAlt', irtifa)
                enlem = data.get('lat', 0.0)
                boylam = data.get('lng', 0.0)
                gyro_x = data.get('eulX', 0.0)
                gyro_y = data.get('eulY', 0.0)
                gyro_z = data.get('eulZ', 0.0)
                pitch = data.get('pitch', 0.0)
                ivme_x = data.get('accX', 0.0)
                ivme_y = data.get('accY', 0.0)
                ivme_z = data.get('accZ', 0.0)
                durum = data.get('state', 1)
            else:
                # Görev yükü formatı - yeni format: {"header":82,"lat":0.000000,"lng":0.000000,"alt":0.0,"rms_internal":0.0020,"rms_external":0.0000}
                irtifa = data.get('alt', 0.0)  # İrtifa - 'alt' alanı
                gps_irtifa = data.get('alt', irtifa)  # GPS irtifa - 'alt' alanı (aynı)
                enlem = data.get('lat', 0.0)  # Enlem - 'lat' alanı
                boylam = data.get('lng', 0.0)  # Boylam - 'lng' alanı
                gyro_x = data.get('gyroX', 0.0)
                gyro_y = data.get('gyroY', 0.0)
                gyro_z = data.get('gyroZ', 0.0)
                pitch = data.get('pitch', 0.0)
                # İvmeler kaldırıldı - 0 değerleri kullanılıyor
                ivme_x = 0.0
                ivme_y = 0.0
                ivme_z = 0.0
                # RMS alanları eklendi
                rms_internal = data.get('rms_internal', 'ovf')
                rms_external = data.get('rms_external', 0.00)
                durum = data.get('durum', 1)
            
            # Mevcut verileri al (eğer yoksa boş dict oluştur)
            current_data = self.telemetry_data.get('fields', {})
            
            # Kaynak bazlı veri işleme
            if kaynak == "anakart":
                # Anakart verilerini ana roket verileri olarak kullan
                current_data.update({
                    'Takım ID': str(self.team_id),
                    'Paket Sayacı': str(self.packet_counter if hasattr(self, 'packet_counter') else 0),
                    'Durum': str(durum),
                    'Açı': f"{pitch:.1f}°",
                    'İrtifa': f"{irtifa:.1f} m",
                    'Roket GPS İrtifa': f"{gps_irtifa:.1f} m",
                    'Roket Enlem': f"{enlem:.6f}°",
                    'Roket Boylam': f"{boylam:.6f}°",
                    'Jiroskop X': f"{gyro_x:.2f}",
                    'Jiroskop Y': f"{gyro_y:.2f}",
                    'Jiroskop Z': f"{gyro_z:.2f}",
                    'Ana Sistem İvme X': f"{ivme_x:.2f}",
                    'Ana Sistem İvme Y': f"{ivme_y:.2f}",
                    'Ana Sistem İvme Z': f"{ivme_z:.2f}"
                })
                
            else:  # gorev_yuku veya bilinmeyen
                # Görev yükü verilerini güncelle - ana sistem verilerini koru
                current_data.update({
                    'Takım ID': str(self.team_id),
                    'Paket Sayacı': str(self.packet_counter if hasattr(self, 'packet_counter') else 0),
                    'Durum': str(durum),
                    'Görev Yükü GPS İrtifa': f"{gps_irtifa:.1f} m",  # Görev yükü GPS irtifa (alt)
                    'Görev Yükü Enlem': f"{enlem:.6f}°",  # Görev yükü enlem (lat)
                    'Görev Yükü Boylam': f"{boylam:.6f}°",  # Görev yükü boylam (lng)
                    'RMS Internal': str(rms_internal),
                    'RMS External': f"{rms_external:.2f}"
                })
                # Ana sistem verilerini koru (eğer varsa)
                if 'Roket GPS İrtifa' not in current_data:
                    current_data.update({
                        'Roket GPS İrtifa': "0.0 m",
                        'Roket Enlem': "0.000000°",
                        'Roket Boylam': "0.000000°",
                        'Jiroskop X': "0.00",
                        'Jiroskop Y': "0.00",
                        'Jiroskop Z': "0.00",
                        'Ana Sistem İvme X': "0.00",
                        'Ana Sistem İvme Y': "0.00",
                        'Ana Sistem İvme Z': "0.00"
                    })
            
            # Telemetri verilerini güncelle
            self.telemetry_data = {'fields': current_data}
            

            
            # Telemetri verisi değişikliğini sinyal et
            self.telemetry_data_changed.emit()
            
            # Verileri sakla (hakem gönderimi timer ile yapılacak)
            if kaynak == 'anakart':
                self.ana_sistem_data = {
                    'altitude': irtifa,
                    'gps_altitude': gps_irtifa,
                    'latitude': enlem,
                    'longitude': boylam,
                    'gyro_x': gyro_x,
                    'gyro_y': gyro_y,
                    'gyro_z': gyro_z,
                    'acc_x': ivme_x,
                    'acc_y': ivme_y,
                    'acc_z': ivme_z,
                    'angle': pitch,
                    'status': durum
                }
            else:  # gorev_yuku
                self.gorev_yuku_data = {
                    'altitude': irtifa,
                    'gps_altitude': gps_irtifa,
                    'latitude': enlem,
                    'longitude': boylam,
                    'rms_internal': rms_internal,
                    'rms_external': rms_external
                }
            
            if kaynak == 'gorev_yuku':
                print(f"[PYTHON] {kaynak} kaynaklı JSON telemetri verisi işlendi: İrtifa: {irtifa}, GPS: {gps_irtifa}, RMS: ({rms_internal}, {rms_external:.2f})")
            else:
                print(f"[PYTHON] {kaynak} kaynaklı JSON telemetri verisi işlendi: İrtifa: {irtifa}, İvme: ({ivme_x:.2f}, {ivme_y:.2f}, {ivme_z:.2f})")
            
        except json.JSONDecodeError as e:
            print(f"[PYTHON] JSON parse hatası: {e}")
        except Exception as e:
            print(f"[PYTHON] Telemetri parse hatası: {e}")

    def _send_telemetry_to_judge(self, telemetry_data, kaynak):
        """Telemetri verilerini hakem yer istasyonuna gönder"""
        try:
            if not self.judge_port or not self.judge_port.isOpen():
                return
                
            # Paket sayacını artır
            self.packet_counter = (self.packet_counter + 1) % 256
            
            # Telemetri verilerinden değerleri al
            if kaynak == 'anakart':
                # Ana sistem verileri - doğrudan eşleştirme
                altitude = telemetry_data.get('alt', 0.0)  # Ana paket irtifa
                rocket_gps_altitude = telemetry_data.get('gpsAlt', 0.0)  # Roket GPS İrtifa
                rocket_latitude = telemetry_data.get('lat', 0.0)  # Roket Enlem
                rocket_longitude = telemetry_data.get('lng', 0.0)  # Roket Boylam
                gyroscope_x = telemetry_data.get('eulX', 0.0)  # Jiroskop X
                gyroscope_y = telemetry_data.get('eulY', 0.0)  # Jiroskop Y
                gyroscope_z = telemetry_data.get('eulZ', 0.0)  # Jiroskop Z
                acceleration_x = telemetry_data.get('accX', 0.0)  # İvme X
                acceleration_y = telemetry_data.get('accY', 0.0)  # İvme Y
                acceleration_z = telemetry_data.get('accZ', 0.0)  # İvme Z
                angle = telemetry_data.get('pitch', 0.0)  # Açı
                status = telemetry_data.get('state', 0)  # Durum
                
                # Görev yükü verileri için varsayılan değerler (0)
                payload_gps_altitude = 0.0
                payload_latitude = 0.0
                payload_longitude = 0.0
                
            else:
                # Görev yükü verileri - yeni format: {"header":82,"lat":0.000000,"lng":0.000000,"alt":0.0,"rms_internal":0.0020,"rms_external":0.0000}
                altitude = telemetry_data.get('alt', 0.0)  # Ana paket irtifa
                payload_gps_altitude = telemetry_data.get('alt', 0.0)  # Görev Yükü GPS İrtifa
                payload_latitude = telemetry_data.get('lat', 0.0)  # Görev Yükü Enlem
                payload_longitude = telemetry_data.get('lng', 0.0)  # Görev Yükü Boylam
                gyroscope_x = telemetry_data.get('gyroX', 0.0)  # Jiroskop X
                gyroscope_y = telemetry_data.get('gyroY', 0.0)  # Jiroskop Y
                gyroscope_z = telemetry_data.get('gyroZ', 0.0)  # Jiroskop Z
                angle = telemetry_data.get('pitch', 0.0)  # Açı
                status = telemetry_data.get('durum', 0)  # Durum
                
                # RMS alanları eklendi
                rms_internal = telemetry_data.get('rms_internal', 'ovf')  # RMS Internal
                rms_external = telemetry_data.get('rms_external', 0.00)  # RMS External
                
                # İvmeler kaldırıldı - 0 değerleri kullanılıyor
                acceleration_x = 0.0  # İvme X (kaldırıldı)
                acceleration_y = 0.0  # İvme Y (kaldırıldı)
                acceleration_z = 0.0  # İvme Z (kaldırıldı)
                
                # Ana sistem verileri için varsayılan değerler (0)
                rocket_gps_altitude = 0.0
                rocket_latitude = 0.0
                rocket_longitude = 0.0
            
            # Kademe verileri için 0 değerleri (kademe yok)
            stage_gps_altitude = 0.0
            stage_latitude = 0.0
            stage_longitude = 0.0
            
            # HYI paketi oluştur - Ana sistem ve görev yükü ayrı veriler
            packet = self.create_hyi_packet(
                self.packet_counter,
                altitude,  # Ana paket irtifa
                rocket_gps_altitude,  # Roket GPS İrtifa (ana sistem)
                rocket_latitude,  # Roket Enlem (ana sistem)
                rocket_longitude,  # Roket Boylam (ana sistem)
                payload_gps_altitude,  # Görev Yükü GPS İrtifa (ayrı)
                payload_latitude,  # Görev Yükü Enlem (ayrı)
                payload_longitude,  # Görev Yükü Boylam (ayrı)
                stage_gps_altitude,  # Kademe GPS İrtifa (0)
                stage_latitude,  # Kademe Enlem (0)
                stage_longitude,  # Kademe Boylam (0)
                gyroscope_x,  # Jiroskop X
                gyroscope_y,  # Jiroskop Y
                gyroscope_z,  # Jiroskop Z
                acceleration_x,  # İvme X
                acceleration_y,  # İvme Y
                acceleration_z,  # İvme Z
                angle,  # Açı
                status  # Durum
            )
            
            # Paketi hakem portuna gönder
            self.judge_port.write(packet)
            print(f"[PYTHON] Hakem yer istasyonuna telemetri verisi gönderildi (Paket: {self.packet_counter}, Kaynak: {kaynak})")
            if kaynak == 'gorev_yuku':
                print(f"[PYTHON] Görev Yükü Verisi: Alt={altitude}, GPS={payload_gps_altitude}, Lat={payload_latitude}, Lng={payload_longitude}")
            else:
                print(f"[PYTHON] Ana Sistem Verisi: Alt={altitude}, GPSAlt={rocket_gps_altitude}, Lat={rocket_latitude}, Lng={rocket_longitude}")
            
        except Exception as e:
            print(f"[PYTHON] Hakem telemetri gönderme hatası: {e}")

    @pyqtSlot(str, int, result=bool)
    def connect_telemetry(self, port_name, baud_rate):
        print(f"[PYTHON] connect_telemetry çağrıldı: {port_name}, {baud_rate}")
        
        # Port adı kontrolü
        if not port_name or port_name == "" or port_name == "Port bulunamadı":
            print("[PYTHON] ❌ Geçersiz port adı!")
            return False
            
        # Baud rate kontrolü
        if baud_rate not in [9600, 19200, 38400, 57600, 115200]:
            print(f"[PYTHON] ❌ Geçersiz baud rate: {baud_rate}")
            return False
        
        try:
            # Mevcut bağlantıyı kapat
            if self.telemetry_port and self.telemetry_port.isOpen():
                self.telemetry_port.close()
                print(f"[PYTHON] Mevcut telemetri bağlantısı kapatıldı")
            
                self.telemetry_port = None
            
            # Yeni port oluştur
            self.telemetry_port = QSerialPort(port_name)
            
            # Port ayarları
            self.telemetry_port.setBaudRate(baud_rate)
            self.telemetry_port.setDataBits(QSerialPort.Data8)
            self.telemetry_port.setParity(QSerialPort.NoParity)
            self.telemetry_port.setStopBits(QSerialPort.OneStop)
            self.telemetry_port.setFlowControl(QSerialPort.NoFlowControl)
            self.telemetry_port.setReadBufferSize(1024)
            
            # Portu aç
            connected = self.telemetry_port.open(QSerialPort.ReadWrite)
            
            if connected:
                print(f"[PYTHON] ✅ Telemetri portu başarıyla açıldı: {port_name} Baud: {baud_rate}")
                self._telemetry_connected = True
                self._telemetry_port_name = port_name
                self.telemetry_port.readyRead.connect(self._read_telemetry_data)
                self.telemetryConnectedChanged.emit()
                self.telemetry_status_changed.emit()
                return True
            else:
                error = self.telemetry_port.error()
                print(f"[PYTHON] ❌ Telemetri portu açılamadı: {port_name}")
                print(f"[PYTHON] Hata kodu: {error}")
                return False
                
        except Exception as e:
            print(f"[PYTHON] ❌ Telemetri bağlantı hatası: {e}")
            return False

    @pyqtSlot()
    def disconnect_telemetry(self):
        print("[PYTHON] disconnect_telemetry çağrıldı")
        try:
            if self.telemetry_port and self.telemetry_port.isOpen():
                self.telemetry_port.close()
                print("[PYTHON] ✅ Telemetri portu kapatıldı")
            else:
                print("[PYTHON] ⚠️ Telemetri portu zaten kapalı")
            
            self._telemetry_connected = False
            self._telemetry_port_name = ""
            self.telemetryConnectedChanged.emit()
            self.telemetry_status_changed.emit()
            
        except Exception as e:
            print(f"[PYTHON] ❌ Telemetri bağlantı kesme hatası: {e}")

    @pyqtSlot(str, int, result=bool)
    def connect_telemetry2(self, port_name, baud_rate):
        print(f"[PYTHON] connect_telemetry2 çağrıldı: {port_name}, {baud_rate}")
        
        # Port adı kontrolü
        if not port_name or port_name == "" or port_name == "Port bulunamadı":
            print("[PYTHON] ❌ Geçersiz port adı!")
            return False
            
        # Baud rate kontrolü
        if baud_rate not in [9600, 19200, 38400, 57600, 115200]:
            print(f"[PYTHON] ❌ Geçersiz baud rate: {baud_rate}")
            return False
        
        try:
            # Mevcut bağlantıyı kapat
            if self.telemetry2_port and self.telemetry2_port.isOpen():
                self.telemetry2_port.close()
                print(f"[PYTHON] Mevcut telemetri2 bağlantısı kapatıldı")
            
                self.telemetry2_port = None
            
            # Yeni port oluştur
            self.telemetry2_port = QSerialPort(port_name)
            
            # Port ayarları
            self.telemetry2_port.setBaudRate(baud_rate)
            self.telemetry2_port.setDataBits(QSerialPort.Data8)
            self.telemetry2_port.setParity(QSerialPort.NoParity)
            self.telemetry2_port.setStopBits(QSerialPort.OneStop)
            self.telemetry2_port.setFlowControl(QSerialPort.NoFlowControl)
            self.telemetry2_port.setReadBufferSize(1024)
            
            # Portu aç
            connected = self.telemetry2_port.open(QSerialPort.ReadWrite)
            
            if connected:
                print(f"[PYTHON] ✅ Telemetri2 portu başarıyla açıldı: {port_name} Baud: {baud_rate}")
                self._telemetry2_connected = True
                self._telemetry2_port_name = port_name
                self.telemetry2_port.readyRead.connect(self._read_telemetry2_data)
                self.telemetry2ConnectedChanged.emit()
                self.telemetry2_status_changed.emit()
                return True
            else:
                error = self.telemetry2_port.error()
                print(f"[PYTHON] ❌ Telemetri2 portu açılamadı: {port_name}")
                print(f"[PYTHON] Hata kodu: {error}")
                return False
                
        except Exception as e:
            print(f"[PYTHON] ❌ Telemetri2 bağlantı hatası: {e}")
            return False

    @pyqtSlot()
    def disconnect_telemetry2(self):
        print("[PYTHON] disconnect_telemetry2 çağrıldı")
        try:
            if self.telemetry2_port and self.telemetry2_port.isOpen():
                self.telemetry2_port.close()
                print("[PYTHON] ✅ Telemetri2 portu kapatıldı")
            else:
                print("[PYTHON] ⚠️ Telemetri2 portu zaten kapalı")
            
            self._telemetry2_connected = False
            self._telemetry2_port_name = ""
            self.telemetry2ConnectedChanged.emit()
            self.telemetry2_status_changed.emit()
            
        except Exception as e:
            print(f"[PYTHON] ❌ Telemetri2 bağlantı kesme hatası: {e}")

    def _read_telemetry_data(self):
        try:
            if self.telemetry_port and self.telemetry_port.isOpen():
                if self.telemetry_port.canReadLine():
                    json_data = self.telemetry_port.readLine().data().decode('utf-8').strip()
                    if json_data:
                        print(f"[PYTHON] JSON verisi alındı (ana sistem): {json_data}")
                        self.parse_telemetry_packet(json_data)
                    else:
                        print("[PYTHON] Boş veri alındı (ana sistem)")
        except Exception as e:
            print(f"[PYTHON] Telemetri okuma hatası (ana sistem): {e}")

    def _read_telemetry2_data(self):
        try:
            if self.telemetry2_port and self.telemetry2_port.isOpen():
                if self.telemetry2_port.canReadLine():
                    try:
                        # Önce UTF-8 olarak decode etmeye çalış
                        json_data = self.telemetry2_port.readLine().data().decode('utf-8').strip()
                        if json_data:
                            print(f"[PYTHON] JSON verisi alındı (görev yükü): {json_data}")
                            self.parse_telemetry_packet(json_data)
                        else:
                            print("[PYTHON] Boş veri alındı (görev yükü)")
                    except UnicodeDecodeError:
                        # UTF-8 decode hatası - binary veri olabilir, atla
                        raw_data = self.telemetry2_port.readLine().data()
                        print(f"[PYTHON] Binary veri alındı (görev yükü), atlanıyor: {raw_data.hex()}")
                        return
        except Exception as e:
            print(f"[PYTHON] Telemetri2 okuma hatası (görev yükü): {e}")

    @pyqtSlot(str, int, result=bool)
    def connect_judge(self, port_name, baud_rate):
        print(f"[PYTHON] connect_judge çağrıldı: {port_name}, {baud_rate}")
        
        # Takım ID kontrolü - hakem bağlantısı için takım ID'nin ayarlanmış olması gerekir
        if self.team_id < 1 or self.team_id > 255:
            print("[PYTHON] ❌ Takım ID ayarlanmamış! Hakem bağlantısı için takım ID 1-255 arasında olmalıdır.")
            return False
        
        # Port adı kontrolü
        if not port_name or port_name == "" or port_name == "Port bulunamadı":
            print("[PYTHON] ❌ Geçersiz port adı!")
            return False
            
        # Baud rate kontrolü
        if baud_rate not in [9600, 19200, 38400, 57600, 115200]:
            print(f"[PYTHON] ❌ Geçersiz baud rate: {baud_rate}")
            return False
        
        try:
            # Mevcut bağlantıyı kapat
            if self.judge_port and self.judge_port.isOpen():
                self.judge_port.close()
                print(f"[PYTHON] Mevcut hakem bağlantısı kapatıldı")
            
                self.judge_port = None
            
            # Yeni port oluştur
            self.judge_port = QSerialPort(port_name)
            
            # Port ayarları
            self.judge_port.setBaudRate(baud_rate)
            self.judge_port.setDataBits(QSerialPort.Data8)
            self.judge_port.setParity(QSerialPort.NoParity)
            self.judge_port.setStopBits(QSerialPort.OneStop)
            self.judge_port.setFlowControl(QSerialPort.NoFlowControl)
            self.judge_port.setReadBufferSize(1024)
            
            # Portu aç
            connected = self.judge_port.open(QSerialPort.ReadWrite)
            
            if connected:
                print(f"[PYTHON] ✅ Hakem portu başarıyla açıldı: {port_name} Baud: {baud_rate}")
                self._judge_connected = True
                self._judge_port_name = port_name
                self.judgeConnectedChanged.emit()
                self.judge_status_changed.emit()
                return True
            else:
                error = self.judge_port.error()
                print(f"[PYTHON] ❌ Hakem portu açılamadı: {port_name}")
                print(f"[PYTHON] Hata kodu: {error}")
                return False
                
        except Exception as e:
            print(f"[PYTHON] ❌ Hakem bağlantı hatası: {e}")
            return False

    @pyqtSlot()
    def disconnect_judge(self):
        print("[PYTHON] disconnect_judge çağrıldı")
        try:
            if self.judge_port and self.judge_port.isOpen():
                self.judge_port.close()
                print("[PYTHON] ✅ Hakem portu kapatıldı")
            else:
                print("[PYTHON] ⚠️ Hakem portu zaten kapalı")
            
            self._judge_connected = False
            self._judge_port_name = ""
            self.judgeConnectedChanged.emit()
            self.judge_status_changed.emit()
            
        except Exception as e:
            print(f"[PYTHON] ❌ Hakem bağlantı kesme hatası: {e}")

    @pyqtProperty('QVariantMap', notify=telemetry_data_changed)
    def telemetry_data_property(self):
        return self.telemetry_data





if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Uygulama meta verilerini ayarla
    app.setApplicationName("111")
    app.setApplicationDisplayName("111 - Roket Telemetri")
    app.setApplicationVersion("1.0")
    
    # Ana uygulama icon'u
    try:
        app.setWindowIcon(QIcon("icon.ico"))
    except:
        # Windows'ta farklı icon yükleme
        try:
            if sys.platform.startswith('win'):
                # Windows'ta icon yükleme
                app.setWindowIcon(QIcon("icon.ico"))
            else:
                # macOS/Linux'ta sistem icon'u
                app.setWindowIcon(QIcon.fromTheme("applications-science"))
        except:
            # Fallback icon
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            app.setWindowIcon(QIcon(pixmap))
    
    # Windows'ta pencere yönetimi için ek ayarlar
    if sys.platform.startswith('win'):
        # Windows'ta title bar ve pencere kontrollerini etkinleştir
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Ana uygulamayı doğrudan başlat
    print("[PYTHON] Ana uygulama başlatılıyor...")
    engine = QQmlApplicationEngine()

    serial_manager = SerialManager()
    
    # Varsayılan takım ID ayarla
    serial_manager.team_id = 1
    print(f"[PYTHON] Varsayılan takım ID ayarlandı: {serial_manager.team_id}")
    
    # Otomatik port bağlantısı devre dışı
    print("[PYTHON] Otomatik port bağlantısı devre dışı bırakıldı")
    
    engine.rootContext().setContextProperty("serialManager", serial_manager)

    # QML kodunu string olarak yükle
    print("[PYTHON] QML engine başlatılıyor...")
    try:
        engine.loadData(QML_CODE.encode('utf-8'))
        print("[PYTHON] QML data yüklendi")
    except Exception as e:
        print(f"[PYTHON] ❌ QML data yükleme hatası: {e}")
        sys.exit(-1)
    
    if not engine.rootObjects():
        print("[PYTHON] ❌ QML engine başarısız oldu!")
        print("[PYTHON] Root objects:", engine.rootObjects())
        sys.exit(-1)
    
    print("[PYTHON] ✅ QML engine başarıyla başlatıldı")
    print("[PYTHON] Root objects sayısı:", len(engine.rootObjects()))
    
    # Root object'ı al ve window'u göster
    root_objects = engine.rootObjects()
    if root_objects:
        main_window = root_objects[0]
        print("[PYTHON] Ana pencere bulundu, gösteriliyor...")
        try:
            main_window.show()
            main_window.raise_()
            main_window.requestActivate()
            print("[PYTHON] Ana pencere gösterildi")
        except Exception as e:
            print(f"[PYTHON] ❌ Pencere gösterme hatası: {e}")
    else:
        print("[PYTHON] ❌ Root object bulunamadı!")
    
    print("[PYTHON] Ana uygulama döngüsü başlatılıyor...")
    
    # Windows'ta daha stabil çalışması için
    if sys.platform.startswith('win'):
        print("[PYTHON] Windows platformu tespit edildi, özel ayarlar uygulanıyor...")
        # Windows'ta QML engine'i daha stabil hale getir
        try:
            # Windows'ta ek güvenlik önlemleri
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("111.RoketTelemetri.1.0")
            
            # Windows'ta pencere yönetimi için ek ayarlar
            app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        except:
            pass
    
    try:
        exit_code = app.exec_()
        print(f"[PYTHON] Uygulama döngüsü bitti, exit code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"[PYTHON] ❌ Uygulama döngüsü hatası: {e}")
        sys.exit(-1)
 