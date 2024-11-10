document.addEventListener('DOMContentLoaded', function () {
    // Hier die Höhe des videoFrame basierend auf der Toolbar-Höhe aktualisieren
    const toolbar = document.getElementById('toolbar');
    const toolbarHeight = toolbar.offsetHeight;
    const videoFrame = document.getElementById('videoFrame');
    videoFrame.style.maxHeight = `calc(100vh - ${toolbarHeight}px)`;

    updateRecordButtonLabel();
});

function showTab(tabId) {
    // Alle Tabs ausblenden
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.classList.remove('active');
    });

    // Alle Tab-Buttons zurücksetzen
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(button => {
        button.classList.remove('active');
    });

    // Den ausgewählten Tab anzeigen
    document.getElementById(tabId).classList.add('active');

    // Den aktiven Button hervorheben
    const activeButton = Array.from(buttons).find(button => {
        // Vergleiche den Textinhalt des Buttons mit dem Tab-Namen
        return button.textContent.trim() === (tabId === 'videoTab' ? 'Video' : 'gespeicherte Dateien');
    });

    if (activeButton) {
        activeButton.classList.add('active');
    }

    getFileList();
}

var socket = io.connect(window.location.protocol + '//'  + document.domain + ':' + location.port);

socket.on('update_frame', function(data) {
    document.getElementById('videoFrame').src = 'data:image/jpeg;base64,' + data.current_frame;
});

// BUTTONS
var recording = false; 

function toggleRecording() {
    recording = !recording;
    sendAjaxRequest("/toggle_recording");
    updateRecordButtonLabel();
}

function updateRecordButtonLabel() {
    var recordButton = document.getElementById('recordButton');

    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/is_recording', true);

    xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
            var response = JSON.parse(xhr.responseText);
            var recording = response.recording;
            var iconColor = recording ? 'red' : 'black';
            var textColor = recording ? 'red' : 'black';

            recordButton.innerHTML = `<i class="fa-solid fa-video" style="color: ${iconColor};"></i> <span style="color: ${textColor};"> ${recording ? 'Stop' : 'Start'} Recording</span>`;
        } else {
            console.error('Failed to fetch recording status');
        }
    };

    xhr.send();
}


function flipImage() {
    sendAjaxRequest("/flip_image");
}

function quit() {
    sendAjaxRequest("/quit");
}

function cycleHud() {
    sendAjaxRequest("/cycle_hud");
}

function takePhoto() {
    sendAjaxRequest("/take_photo");
}

function rotateImage() {
    sendAjaxRequest("/rotate_image");
}

function getFileList() {
    sendAjaxRequestWithResponse("/get_file_list");
}

function sendAjaxRequestWithResponse(url) {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            displayFileList(response);
        }
    };
    xhr.send();
}

function displayFileList(fileList) {
    const fileListContainer = document.getElementById('fileListContainer');
    fileListContainer.innerHTML = '';

    fileList.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';

        const fileName = document.createElement('span');
        fileName.textContent = `${file.name}.${file.ending}`;

        const downloadButton = document.createElement('button');
        downloadButton.textContent = 'Download';
        downloadButton.onclick = function() {
            downloadFile(file.filename);
        };

        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Löschen';
        deleteButton.onclick = function() {
            if (confirm(`Möchten Sie die Datei "${file.filename}" wirklich löschen?`)) {
                deleteFile(file.filename);
            }
        };

        fileItem.appendChild(fileName);
        fileItem.appendChild(downloadButton);
        fileItem.appendChild(deleteButton);
        fileListContainer.appendChild(fileItem);
    });
}


function downloadFile(filename) {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", `/download_file/${encodeURIComponent(filename)}`, true);
    xhr.responseType = 'blob';
    xhr.onload = function () {
        if (xhr.status === 200) {
            const blob = new Blob([xhr.response], { type: xhr.getResponseHeader('Content-Type') });
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else {
            console.error('Download fehlgeschlagen:', xhr.statusText);
        }
    };
    xhr.send();
}

function deleteFile(filename) {
    const xhr = new XMLHttpRequest();
    xhr.open("DELETE", `/delete_file/${encodeURIComponent(filename)}`, true);
    xhr.onload = function () {
        if (xhr.status === 200) {
            console.log('Datei erfolgreich gelöscht:', filename);
            getFileList();
        } else {
            console.error('Fehler beim Löschen der Datei:', xhr.statusText);
        }
    };
    xhr.send();
}

function sendAjaxRequest(url) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.send();
}

// TARGET
document.getElementById('videoFrame').addEventListener('click', function(event) {
    var image = document.getElementById('videoFrame');
    var x = event.offsetX / image.width;
    var y = event.offsetY / image.height;

    sendCoordinatesToServer(x, y);
});

function sendCoordinatesToServer(x, y) {
    var xhr = new XMLHttpRequest();
    var url = "/send_coordinates";
    url += "?x=" + encodeURIComponent(x) + "&y=" + encodeURIComponent(y);

    xhr.open("GET", url, true);
    xhr.send();
}