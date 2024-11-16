// const SERVER_IP = "spotify-sync.ditto.rlab.uk";
const SERVER_IP = 'localhost:8000';
const socket = new WebSocket('ws://' + SERVER_IP + '/ws/download');  // Connect to WebSocket
const SERVER_API = 'http://' + SERVER_IP;  // API base URL

// Show a toast message
function showToast(message, type) {
    const toast = document.createElement('div');
    toast.classList.add('flex', 'items-center', 'p-4', 'rounded-lg', 'shadow-md',
        'text-white', 'animate-fade-in-out', 'mx-auto', 'my-4',
        type === 'success' ? 'bg-green-600' : 'bg-red-600');
    toast.style.width = '50%';
    toast.innerHTML = `
        <span class="material-icons">${type === 'success' ? 'check_circle' : 'error'}</span>
        <span>${message}</span>
    `;

    // Append toast to the container
    const toastContainer = document.getElementById('toast-container');
    toastContainer.appendChild(toast);
}

function addToDownloads(data) {
    const downloadTracks = document.getElementById('downloaded-tracks');
    showDownloadDot();
    // Generate a unique ID based on track title and artist to ensure uniqueness
    const trackId = `${data.track.title}-${data.track.artist}`;
    
    // Check if the track already exists
    let trackItem = document.getElementById(trackId);
    
    // If the track item doesn't exist, create a new one
    if (!trackItem) {
        trackItem = document.createElement('div');
        trackItem.id = trackId; // Unique ID for each track
        trackItem.classList.add('flex', 'justify-between', 'items-center', 'p-4', 'bg-gray-800', 'rounded-lg', 'shadow-md', 'mb-2');
        
        // Basic track info (this won't change unless the title or artist changes)
        const trackInfo = `
            <div>
            <a href="${data.track.url}" target="_blank">
                <p class="text-sm font-semibold text-white">${data.track.title} - ${data.track.artist}</p>
                <p class="text-xs text-gray-400">${data.playlist}</p>
            </a>
            </div>
        `;
        
        // Append basic track info to the track item
        trackItem.innerHTML = trackInfo;
        downloadTracks.appendChild(trackItem);
    }
    
    // Status-specific messages and styles
    let statusMessage = '';
    let additionalContent = '';
    
    switch (data.status) {
        case 'Downloading':
            statusMessage = `<span class="text-xs text-yellow-400">Downloading... ${data.progress}%</span>`;
            additionalContent = `
                <div class="w-full bg-gray-600 rounded-full h-1">
                    <div class="bg-green-400 h-1" style="width: ${data.progress}%"></div>
                </div>
            `;
            break;
        
        case 'Failed':
            statusMessage = `<span class="text-xs text-red-400">Failed</span>`;
            break;
        
        case 'Already Downloaded':
            statusMessage = `<span class="text-xs text-orange-400">Already Downloaded</span>`;
            break;
        
        case 'Downloaded':
            statusMessage = `<span class="text-xs text-green-400">Downloaded</span>`;
            break;
        
        default:
            statusMessage = `<span class="text-xs text-gray-400">Unknown status</span>`;
    }
    
    // Update the track item with the latest status and progress
    trackItem.innerHTML = `
        ${trackItem.innerHTML.split('</div>')[0]}</div> <!-- Preserve the track info part -->
        <div class="space-x-3">
            ${statusMessage}
            ${additionalContent}
        </div>
    `;
}

// Handle WebSocket messages
socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log(data);
    addToDownloads(data);  // Update UI based on message from WebSocket
};


function showDownloadDot() {
    const downloadDot = document.getElementById('download-dot');
    downloadDot.classList.remove('hidden');  // Make the dot visible
}

// Function to hide the download dot
function hideDownloadDot() {
    const downloadDot = document.getElementById('download-dot');
    downloadDot.classList.add('hidden');  // Hide the dot
}


// Function to trigger the download process via the API
async function downloadData() {
    try {
        const response = await fetch(SERVER_API + '/download');
        const data = await response.json();
        showToast(data.message || 'Download started!', 'success');
        socket.onerror = function(event) {
            showToast("WebSocket error: " + event.message, "error");
        };

        socket.onclose = function(event) {
            showToast("WebSocket connection closed.", "info");
        };
    } catch (e) {
        showToast('Error during download: ' + e.message, 'error');
    }
}


// Modal show/hide functionality
const scrollTopButton = document.getElementById('scroll-top');
const downloadModal = document.getElementById('download-modal');
const closeModalButton = document.getElementById('close-modal');

// Toggle modal visibility when the button is clicked
scrollTopButton.addEventListener('click', () => {
    downloadModal.classList.toggle('hidden'); // Show/hide modal
});

// Close the modal when the close button is clicked
closeModalButton.addEventListener('click', () => {
    downloadModal.classList.add('hidden'); // Hide modal
});



// Trigger playlist load on page load
document.addEventListener('DOMContentLoaded', function () {
    // Set event listeners for sync and download buttons
    document.querySelector('#sync-btn').addEventListener('click', syncData);
    document.querySelector('#download-btn').addEventListener('click', downloadData);

    // Show loading spinner while fetching playlists
    document.querySelector('#loading').classList.remove('hidden');

    // Start loading playlists
    fetchPlaylists();
});


async function fetchPlaylists() {
    try {
        const response = await fetch(SERVER_API + '/playlists');
        const data = await response.json(); // Parse the JSON response
        
        // Check if the response contains an error
        if (data.detail && data.detail.error) {
            showToast(data.detail.error, 'error');
            // If an authorization URL is provided, redirect to it
            if (data.detail.auth_url) {
                window.location.href = data.detail.auth_url;
            }
            return;
        }

        if (Array.isArray(data) && data.length > 0) {
            // Hide loading spinner
            document.querySelector('#loading').classList.add('hidden');

            // Display the playlists
            const playlistContainer = document.getElementById('playlist-output');
            playlistContainer.innerHTML = ''; // Clear previous playlists

            // Iterate over playlists and display them in a list format
            data.forEach(playlist => {
                const listItem = document.createElement('div');
                listItem.classList.add('cursor-pointer', 'hover:bg-gray-700', 'px-4', 'py-2', 'rounded-md');

                listItem.innerHTML = `
                    <div class="flex items-center">
                            <span class="font-semibold text-white">${playlist.name}</span>
                    </div>
                `;

                // Add click event to load playlist tracks when selected
                listItem.addEventListener('click', () => loadTracks(playlist));

                // Append list item to the playlist container
                playlistContainer.appendChild(listItem);
            });

        } else {
            console.error('No playlists found or invalid response format');
            document.querySelector('#loading').classList.add('hidden');
        }
    } catch (e) {
        console.error("Error fetching playlists:", e);
        document.querySelector('#loading').classList.add('hidden');
    }
}

// Load tracks for the selected playlist
function loadTracks(playlist) {
    const trackContainer = document.getElementById('track-output');
    const playlistContainer = document.getElementById('playlist-output');
    
    trackContainer.innerHTML = '';
    // if screen is small, hide playlist menu and show back button to go back to playlist menu
    if (window.innerWidth < 1024) {
        playlistContainer.classList.add('hidden');
        trackContainer.classList.remove('hidden');
    }
    
    const backButton = document.createElement('button');
    backButton.classList.add('bg-gray-600', 'text-white', 'py-2', 'px-4', 'rounded-lg', 'my-4');
    backButton.textContent = 'Back to Playlist';
    backButton.addEventListener('click', () => {
        trackContainer.innerHTML = ''; // Clear tracks

        if (window.innerWidth < 1024) {
            playlistContainer.classList.remove('hidden');
            trackContainer.classList.add('hidden');
        }
    });
    
    trackContainer.appendChild(backButton); // Add back button

    playlist.tracks.forEach(track => {
        const trackItem = document.createElement('div');
        trackItem.classList.add('flex', 'justify-between', 'items-center', 'p-4', 'bg-gray-800', 'rounded-lg', 'shadow-md', 'mb-2');

        trackItem.innerHTML = `
            <img src="${track.image}" alt="${track.name}" class="w-12 h-12 rounded-lg mr-4">
            <div>
                <p class="text-sm font-semibold text-white">${track.name}</p>
                <p class="text-xs text-gray-400">${track.artist} - ${track.album}</p>
            </div>
            <div class="space-x-3">
                <span class="text-xs ${track.isSynced ? 'text-green-400' : 'text-red-400'}">${track.isSynced ? 'Synced' : 'Not Synced'}</span>
                <span class="text-xs ${track.isDownloaded ? 'text-green-400' : 'text-red-400'}">${track.isDownloaded ? 'Downloaded' : 'Not Downloaded'}</span>
            </div>
        `;

        trackContainer.appendChild(trackItem);
    });
}


document.addEventListener("DOMContentLoaded", function () {
    const playlistContainer = document.getElementById("playlist-output");
    const trackContainer = document.getElementById("track-output");

    // Function to toggle visibility based on screen size
    function handleResize() {
        if (window.innerWidth >= 1024) {
            playlistContainer.classList.remove("hidden");
            trackContainer.classList.remove("hidden");
        } else {
            trackContainer.classList.add("hidden");
        }
    }

    // Event listener for resizing the window
    window.addEventListener("resize", handleResize);

    // Initialize on page load
    handleResize();

    // Back button logic
    trackContainer.addEventListener("click", function (e) {
        if (e.target.id === "back-btn") {
            trackContainer.classList.add("hidden");
            playlistContainer.classList.remove("hidden");
        }
    });

    // Load tracks function update
    window.loadTracks = function (playlist) {
        trackContainer.innerHTML = `
            <button id="back-btn" class="bg-gray-900 text-white py-2 px-4 rounded-lg my-4">
                Back to Playlist
            </button>
        `;

        if (window.innerWidth < 1024) {
            playlistContainer.classList.add("hidden");
            trackContainer.classList.remove("hidden");
        }

        playlist.tracks.forEach(track => {
            const trackItem = document.createElement("div");
            trackItem.classList.add(
                "flex", "justify-between", "items-center", "hover:bg-gray-900",
                "p-4", "bg-gray-800", "rounded-lg", "shadow-md", "mb-2"
            );

            trackItem.innerHTML = `
                <img src="${track.image}" alt="${track.name}" class="w-12 h-12 rounded-lg mr-4">
                <div>
                    <p class="text-sm font-semibold text-white">${track.name}</p>
                    <p class="text-xs text-gray-400">${track.artist} - ${track.album}</p>
                </div>
                <div class="space-x-3">
                    <span class="text-xs ${track.isSynced ? 'text-green-400' : 'text-red-400'}">
                        ${track.isSynced ? 'Synced' : 'Not Synced'}
                    </span>
                    <span class="text-xs ${track.isDownloaded ? 'text-green-400' : 'text-red-400'}">
                        ${track.isDownloaded ? 'Downloaded' : 'Not Downloaded'}
                    </span>
                </div>
            `;

            trackContainer.appendChild(trackItem);
        });
    };
});

// Toast function
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    
    // Create a new toast element
    const toast = document.createElement('div');
    toast.classList.add(
        'flex', 'items-center', 'p-4', 'rounded-lg', 'shadow-md', 
        'text-white', 'animate-fade-in-out', 
        type === 'success' ? 'bg-green-600' : 'bg-red-600'
    );
    
    toast.innerHTML = `
        <div class="flex items-center">
            <span class="material-icons mr-2">${type === 'success' ? 'check_circle' : 'error'}</span>
            <span>${message}</span>
        </div>
    `;
    
    // Append toast to the container
    container.appendChild(toast);
    
    // Automatically remove toast after 3 seconds
    setTimeout(() => {
        toast.classList.add('opacity-0');
        setTimeout(() => toast.remove(), 500); // Give time for the fade-out animation
    }, 3000);
}

// Sync function updated with toast
async function syncData() {
    try {
        const response = await fetch(SERVER_API + '/sync');
        const data = await response.json();
        showToast(data.message || 'Sync completed successfully!', 'success');
    } catch (e) {
        showToast('Error during sync: ' + e.message, 'error');
    }
}
