/**
 * UISI Shuttle - Shared Map Functions
 * Digunakan oleh pengguna dan driver
 */

let map;
let userMarker = null;
let driverMarkers = {};
let locationMarkers = [];
let userLocation = null;
let locationControl = null;

// Initialize map
function initMap(centerLat = -7.1645, centerLng = 112.6285, zoom = 16) {
	map = L.map('map').setView([centerLat, centerLng], zoom);
	
	L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
		attribution: '© OpenStreetMap contributors',
		maxZoom: 19
	}).addTo(map);

	// Add map controls
	L.control.scale().addTo(map);
	
	if (!document.getElementById('driver-marker-styles')) {
		const style = document.createElement('style');
		style.id = 'driver-marker-styles';
		style.textContent = `
			.driver-marker-icon {
				width: 32px !important;
				height: 32px !important;
				margin-left: -16px !important;
				margin-top: -16px !important;
				font-size: 24px;
				line-height: 32px;
				text-align: center;
				filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
			}
		`;
		document.head.appendChild(style);
	}

	return map;
}

// Create location button control (singleton pattern)
function createLocationButton(onClickCallback) {
	// Remove existing control if any
	if (locationControl) {
		map.removeControl(locationControl);
	}
	
	const LocationControl = L.Control.extend({
		onAdd: function(map) {
			const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
			
			container.innerHTML = `
				<button id="locate-btn" style="
					background: white;
					width: 34px;
					height: 34px;
					border: none;
					cursor: pointer;
					font-size: 18px;
					display: flex;
					align-items: center;
					justify-content: center;
					border-radius: 4px;
					box-shadow: 0 1px 5px rgba(0,0,0,0.4);
				" title="Deteksi lokasi saya">
					📍
				</button>
			`;
			
			container.onclick = function(e) {
				e.stopPropagation();
				if (onClickCallback) onClickCallback();
			};
			
			return container;
		}
	});
	
	locationControl = new LocationControl({ position: 'topleft' });
	locationControl.addTo(map);
	return locationControl;
}

// Get user's current location
function getUserLocation(successCallback, errorCallback) {
	if (!navigator.geolocation) {
		if (errorCallback) errorCallback({ code: 0, message: 'Browser tidak mendukung Geolocation' });
		return;
	}

	// Show loading state on button
	const locateBtn = document.getElementById('locate-btn');
	if (locateBtn) {
		locateBtn.innerHTML = '⏳';
		locateBtn.disabled = true;
	}
	
	navigator.geolocation.getCurrentPosition(
		(position) => {
			const { latitude, longitude, accuracy } = position.coords;
			
			userLocation = { latitude, longitude, accuracy };
			
			// Remove old marker if exists
			if (userMarker) {
				map.removeLayer(userMarker);
			}
			
			// Create custom icon for user
			const userIcon = L.divIcon({
				className: 'user-location-marker',
				html: '<div style="background: #4285F4; width: 16px; height: 16px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(66, 133, 244, 0.5);"></div>',
				iconSize: [22, 22],
				iconAnchor: [11, 11]
			});
			
			// Add user marker
			userMarker = L.marker([latitude, longitude], { icon: userIcon })
				.addTo(map)
				.bindPopup(`
					<strong>📍 Lokasi Anda</strong><br>
					Akurasi: ${Math.round(accuracy)}m
				`);
			
			// Add accuracy circle
			L.circle([latitude, longitude], {
				radius: accuracy,
				color: '#4285F4',
				fillColor: '#4285F4',
				fillOpacity: 0.1,
				weight: 1
			}).addTo(map);
			
			// Center map to user location
			map.setView([latitude, longitude], 17);
			
			// Restore button state
			if (locateBtn) {
				locateBtn.innerHTML = '📍';
				locateBtn.disabled = false;
			}
			
			// Call success callback
			if (successCallback) successCallback(userLocation);
		},
		(error) => {
			// Restore button state
			if (locateBtn) {
				locateBtn.innerHTML = '📍';
				locateBtn.disabled = false;
			}
			
			// Call error callback
			if (errorCallback) errorCallback(error);
		},
		{
			enableHighAccuracy: true,
			timeout: 10000,
			maximumAge: 0
		}
	);
}

// Load and display locations on map
function loadLocationsOnMap(locations, addToSelect = false, fromSelectId = null, toSelectId = null) {
	// Clear existing markers
	locationMarkers.forEach(marker => map.removeLayer(marker));
	locationMarkers = [];
	
	// Add to select if needed
	if (addToSelect && fromSelectId && toSelectId) {
		const fromSelect = document.getElementById(fromSelectId);
		const toSelect = document.getElementById(toSelectId);
		
		// Clear existing options (keep first option - placeholder)
		fromSelect.innerHTML = '<option value="">Pilih lokasi penjemputan...</option>';
		toSelect.innerHTML = '<option value="">Pilih lokasi tujuan...</option>';
	}
	
	locations.forEach(loc => {
		// Add to select options if needed
		if (addToSelect && fromSelectId && toSelectId) {
			const fromSelect = document.getElementById(fromSelectId);
			const toSelect = document.getElementById(toSelectId);
			fromSelect.innerHTML += `<option value="${loc.id}">${loc.name}</option>`;
			toSelect.innerHTML += `<option value="${loc.id}">${loc.name}</option>`;
		}
		
		// Create custom icon for locations
		const locationIcon = L.divIcon({
			className: 'location-marker',
			html: `
				<div style="
					background: #34A853;
					color: white;
					padding: 8px 12px;
					border-radius: 20px;
					font-weight: bold;
					font-size: 12px;
					white-space: nowrap;
					box-shadow: 0 2px 8px rgba(0,0,0,0.3);
					border: 2px solid white;
				">
					${loc.name}
				</div>
			`,
			iconSize: [120, 40],
			iconAnchor: [60, 40]
		});
		
		// Add location marker
		const marker = L.marker([loc.latitude, loc.longitude], { icon: locationIcon })
			.addTo(map)
			.bindPopup(`
				<strong>${loc.name}</strong><br>
				${loc.description || ''}<br>
				<small>${loc.address || ''}</small>
			`);
		
		locationMarkers.push(marker);
	});
}

function updateDriverMarker(driverId, location) {
	// Remove old marker if exists
	if (driverMarkers[driverId]) {
		map.removeLayer(driverMarkers[driverId]);
	}
	
	const driverIcon = L.divIcon({
		className: 'driver-marker-icon',
		html: '🚗',
		// html: `
		// 	<div style="
		// 		position: relative;
		// 		width: 32px;
		// 		height: 32px;
		// 	">
		// 		<div style="
		// 			position: absolute;
		// 			top: 50%;
		// 			left: 50%;
		// 			transform: translate(-50%, -50%) rotate(${location.heading || 0}deg);
		// 			font-size: 24px;
		// 			line-height: 1;
		// 			filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
		// 		">
		// 			🚗
		// 		</div>
		// 	</div>
		// `,
		iconSize: [32, 32],
		iconAnchor: [16, 16],
		popupAnchor: [0, -16]
	});
	
	// Add driver marker
	const marker = L.marker([location.latitude, location.longitude], { 
		icon: driverIcon,
		rotationAngle: location.heading || 0
	}).addTo(map)

	const markerElement = marker._icon;
	if (markerElement && location.heading !== undefined) {
		markerElement.style.transform += ` rotate(${location.heading}deg)`;
	}

	marker.bindPopup(`
		<strong>🚗 Driver #${driverId}</strong><br>
		Kecepatan: ${Math.round(location.speed || 0)} km/h<br>
		Heading: ${Math.round(location.heading || 0)}°<br>
		<small>Update: ${new Date(location.timestamp).toLocaleTimeString('id-ID')}</small>
	`);
	
	driverMarkers[driverId] = marker;
}

// Track specific driver (center map on driver)
function trackDriverOnMap(driverId, notFoundCallback) {
	if (driverMarkers[driverId]) {
		const marker = driverMarkers[driverId];
		map.setView(marker.getLatLng(), 17);
		marker.openPopup();
		return true;
	} else {
		if (notFoundCallback) notFoundCallback();
		return false;
	}
}

// Calculate distance using Haversine formula
function calculateDistance(lat1, lon1, lat2, lon2) {
	const R = 6371; // Earth radius in km
	const dLat = (lat2 - lat1) * Math.PI / 180;
	const dLon = (lon2 - lon1) * Math.PI / 180;
	
	const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
		Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
		Math.sin(dLon/2) * Math.sin(dLon/2);
	
	const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
	return R * c;
}

// Auto-select nearest pickup location
function autoSelectNearestLocation(locations, fromSelectId) {
	if (!userLocation) return null;
	
	let nearestLocation = null;
	let minDistance = Infinity;
	
	locations.forEach(loc => {
		const distance = calculateDistance(
			userLocation.latitude,
			userLocation.longitude,
			loc.latitude,
			loc.longitude
		);
		
		if (distance < minDistance) {
			minDistance = distance;
			nearestLocation = loc;
		}
	});
	
	if (nearestLocation && fromSelectId) {
		document.getElementById(fromSelectId).value = nearestLocation.id;
	}
	
	return nearestLocation ? { location: nearestLocation, distance: minDistance } : null;
}

// Clear all driver markers
function clearDriverMarkers() {
	Object.values(driverMarkers).forEach(marker => {
		map.removeLayer(marker);
	});
	driverMarkers = {};
}

// Get current user location (without fetching new)
function getCurrentUserLocation() {
	return userLocation;
}

// Get map instance
function getMapInstance() {
	return map;
}
