'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Issue, DecayForecast } from '@/lib/api';
import 'leaflet/dist/leaflet.css';

interface InteractiveMapProps {
  issues: Issue[];
  mapMode: 'pins' | 'heatmap' | 'decay';
  selectedIssueId: string | null;
  onSelectIssueId: (id: string | null) => void;
  activeWard: string;
  decayForecasts: DecayForecast[];
}

const WARD_COORDS: Record<string, { lat: number; lng: number }> = {
  "Indiranagar": { lat: 12.97189, lng: 77.6413 },
  "Koramangala": { lat: 12.93453, lng: 77.6265 },
  "Whitefield": { lat: 12.9698, lng: 77.7499 },
  "Jayanagar": { lat: 12.9292, lng: 77.5824 },
  "Malleshwaram": { lat: 12.9978, lng: 77.5685 },
  "HSR Layout": { lat: 12.9116, lng: 77.6784 }
};

const WARD_BOUNDS_COORDS: Record<string, { north: number; south: number; east: number; west: number }> = {
  "Indiranagar": { north: 12.985, south: 12.960, east: 77.655, west: 77.625 },
  "Koramangala": { north: 12.948, south: 12.920, east: 77.640, west: 77.610 },
  "Whitefield": { north: 12.990, south: 12.950, east: 77.770, west: 77.730 },
  "Jayanagar": { north: 12.942, south: 12.915, east: 77.595, west: 77.570 },
  "Malleshwaram": { north: 13.010, south: 12.985, east: 77.580, west: 77.555 },
  "HSR Layout": { north: 12.925, south: 12.895, east: 77.660, west: 77.630 }
};

export default function InteractiveMap({
  issues,
  mapMode,
  selectedIssueId,
  onSelectIssueId,
  activeWard,
  decayForecasts
}: InteractiveMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const layersRef = useRef<any>(null);
  const LRef = useRef<any>(null);
  const userMarkerRef = useRef<any>(null);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);

  // 1. Initial Map Setup
  useEffect(() => {
    let active = true;

    async function initMap() {
      if (!mapContainerRef.current) return;

      const L = await import('leaflet');
      LRef.current = L;

      if (!active) return;

      // Fix Leaflet Default Icon Path Errors in NextJS
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.1/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.1/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.1/images/marker-shadow.png',
      });

      const initialCenter = WARD_COORDS[activeWard] || { lat: 12.97189, lng: 77.6413 };

      // Initialize Map
      const map = L.map(mapContainerRef.current, {
        zoomControl: false,
        attributionControl: false,
        zoomAnimation: true,
        fadeAnimation: true
      }).setView([initialCenter.lat, initialCenter.lng], 13);

      mapRef.current = map;

      // Dark Mode Styled CartoDB Tiles (Premium Dark Theme Map)
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap &copy; CARTO'
      }).addTo(map);

      // Add Zoom Control to Bottom Left
      L.control.zoom({ position: 'bottomleft' }).addTo(map);

      // Initialize Layers Group
      layersRef.current = L.layerGroup().addTo(map);

      // Trigger user geolocation
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            setUserLocation({ lat, lng });
            
            if (active && mapRef.current) {
              mapRef.current.setView([lat, lng], 14);
            }
          },
          (err) => console.log('Geolocation permission denied / failed: ', err),
          { enableHighAccuracy: true }
        );
      }
    }

    if (!mapRef.current) {
      initMap();
    }

    return () => {
      active = false;
    };
  }, []);

  // 2. Pan to Active Ward when it changes (if user location doesn't override initially)
  useEffect(() => {
    if (mapRef.current && activeWard && WARD_COORDS[activeWard]) {
      const coords = WARD_COORDS[activeWard];
      mapRef.current.setView([coords.lat, coords.lng], 13.5);
    }
  }, [activeWard]);

  // 3. Render markers & overlays based on filters, mode, and selection
  useEffect(() => {
    const map = mapRef.current;
    const layers = layersRef.current;
    const L = LRef.current;

    if (!map || !layers || !L) return;

    // Clear existing layer content
    layers.clearLayers();

    // Render User Location if available
    if (userLocation) {
      const userIcon = L.divIcon({
        className: 'user-location-marker',
        html: `<div class="user-pulse-container">
                 <div class="user-pulse-dot"></div>
                 <div class="user-pulse-ripple"></div>
               </div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      userMarkerRef.current = L.marker([userLocation.lat, userLocation.lng], { icon: userIcon })
        .addTo(layers)
        .bindPopup('<b class="text-gray-900">Your Current Location</b><br/><small class="text-gray-600">Reports filed here will automatically resolve in your ward.</small>');
    }

    // Render based on Map Mode
    if (mapMode === 'pins') {
      issues.forEach(issue => {
        const isCritical = issue.aiAnalysis.severityScore >= 8;
        const isSelected = selectedIssueId === issue.id;

        const categoriesColors: Record<string, string> = {
          'POTHOLE': '#EF233C',
          'WATER_LEAK': '#14BDBC',
          'STREETLIGHT': '#F4A261',
          'WASTE': '#52B788',
          'ROAD_DAMAGE': '#EF233C',
          'ENCROACHMENT': '#F7C59F',
          'SEWAGE': '#9d4edd'
        };

        const color = categoriesColors[issue.category] || '#14BDBC';

        // Draw custom styled HTML marker
        const pinIcon = L.divIcon({
          className: 'custom-pin-marker',
          html: `<div class="custom-pin-element" style="
                   background-color: ${color}; 
                   box-shadow: 0 0 10px ${color}; 
                   width: ${isSelected ? '14px' : '10px'}; 
                   height: ${isSelected ? '14px' : '10px'}; 
                   border: 2px solid #ffffff; 
                   border-radius: 50%;
                   transition: all 0.2s ease;
                   transform: scale(${isSelected ? '1.4' : '1'});
                 "></div>`,
          iconSize: [16, 16],
          iconAnchor: [8, 8]
        });

        const marker = L.marker([issue.location.lat, issue.location.lng], { icon: pinIcon })
          .addTo(layers);

        marker.on('click', () => {
          onSelectIssueId(issue.id);
        });
      });
    } else if (mapMode === 'heatmap') {
      issues.forEach(issue => {
        const severity = issue.aiAnalysis.severityScore;
        const radius = 30 + (severity * 6);
        const color = severity >= 8 ? '#EF233C' : severity >= 6 ? '#F4A261' : '#14BDBC';

        L.circle([issue.location.lat, issue.location.lng], {
          color: color,
          fillColor: color,
          fillOpacity: 0.35,
          radius: radius,
          stroke: false
        }).addTo(layers);
      });
    } else if (mapMode === 'decay') {
      decayForecasts.forEach(forecast => {
        const bounds = WARD_BOUNDS_COORDS[forecast.ward];
        if (!bounds) return;

        const color = forecast.riskLevel === 'CRITICAL' ? '#EF233C' 
                    : forecast.riskLevel === 'HIGH' ? '#F4A261' 
                    : forecast.riskLevel === 'MEDIUM' ? '#F7C59F' 
                    : '#52B788';

        L.rectangle([[bounds.south, bounds.west], [bounds.north, bounds.east]], {
          color: color,
          weight: 1.5,
          dashArray: '5, 5',
          fillColor: color,
          fillOpacity: 0.12
        }).addTo(layers);
      });
    }
  }, [issues, mapMode, selectedIssueId, userLocation, decayForecasts]);

  // Recenter when selected issue changes
  useEffect(() => {
    if (mapRef.current && selectedIssueId) {
      const issue = issues.find(x => x.id === selectedIssueId);
      if (issue) {
        mapRef.current.setView([issue.location.lat, issue.location.lng], 15.5);
      }
    }
  }, [selectedIssueId, issues]);

  return (
    <div className="w-full h-full relative">
      {/* Geolocation Loading Indicator */}
      {!userLocation && (
        <div className="absolute top-20 right-4 z-20 bg-civic-surface/90 border border-civic-border/40 px-3 py-1.5 rounded-lg text-[10px] text-civic-text-muted font-bold flex items-center space-x-1.5 animate-pulse">
          <span className="h-1.5 w-1.5 rounded-full bg-civic-teal"></span>
          <span>Acquiring location...</span>
        </div>
      )}
      
      {/* Actual Map Target Element */}
      <div ref={mapContainerRef} className="w-full h-full" style={{ background: '#0a1628' }} />

      {/* Global CSS Inject for User Geolocation Marker animations */}
      <style jsx global>{`
        .user-pulse-container {
          position: relative;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .user-pulse-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #3b82f6;
          border: 2px solid #ffffff;
          box-shadow: 0 0 10px rgba(59, 130, 246, 0.8);
          z-index: 5;
        }
        .user-pulse-ripple {
          position: absolute;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: rgba(59, 130, 246, 0.4);
          animation: user-ripple 1.8s infinite ease-out;
          pointer-events: none;
        }
        @keyframes user-ripple {
          0% {
            transform: scale(0.4);
            opacity: 1;
          }
          100% {
            transform: scale(1.6);
            opacity: 0;
          }
        }
        .leaflet-container {
          background-color: #070e17 !important;
        }
        .leaflet-bar {
          border: 1px solid rgba(255, 255, 255, 0.1) !important;
          background: rgba(10, 22, 40, 0.85) !important;
          backdrop-filter: blur(8px) !important;
          border-radius: 8px !important;
          overflow: hidden;
        }
        .leaflet-bar a {
          background: transparent !important;
          color: #ffffff !important;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
          font-weight: bold;
        }
        .leaflet-bar a:hover {
          background: rgba(255, 255, 255, 0.1) !important;
        }
      `}</style>
    </div>
  );
}
