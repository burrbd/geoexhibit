/**
 * GeoExhibit Web Map Application
 * Integrates PMTiles vector features with TiTiler raster layers
 */

class GeoExhibitMap {
    constructor() {
        this.map = null;
        this.pmtilesLayer = null;
        this.rasterLayers = new Map();
        this.features = [];
        this.items = [];
        this.dates = [];
        this.currentDateIndex = 0;
        this.selectedFeature = null;
        this.config = {
            pmtilesPath: '../pmtiles/features.pmtiles',
            stacBasePath: '../stac/',
            tilerBaseUrl: null, // Will be set from URL params or default to relative paths
            jobId: null // Will be set from URL params or config
        };
        
        this.init();
    }
    
    async init() {
        this.initMap();
        await this.loadPMTiles();
        await this.loadSTACCollection();
        this.initControls();
        this.updateStatus('✅ Map ready', 'success');
    }
    
    initMap() {
        // Initialize Leaflet map centered on Australia
        this.map = L.map('map').setView([-35.0, 138.0], 6);
        
        // Add base tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
        
        // Add map click handler
        this.map.on('click', (e) => this.handleMapClick(e));
    }
    
    async loadPMTiles() {
        try {
            this.updateStatus('Loading features...', 'loading');
            
            // Create PMTiles source
            const protocol = new pmtiles.Protocol();
            L.PMTiles = protocol;
            
            // Add PMTiles layer
            this.pmtilesLayer = protomaps.leafletLayer({
                url: this.config.pmtilesPath,
                theme: {
                    'default': {
                        'fill': '#ff6b6b',
                        'fill-opacity': 0.6,
                        'stroke': '#d63031',
                        'stroke-width': 2
                    }
                }
            });
            
            this.pmtilesLayer.addTo(this.map);
            
            // Load feature properties for the UI
            await this.extractFeatureProperties();
            
        } catch (error) {
            console.error('PMTiles loading failed:', error);
            this.updateStatus('⚠️ PMTiles loading failed (features not available)', 'error');
        }
    }
    
    async extractFeatureProperties() {
        // For now, use mock features until we can read PMTiles metadata
        // In production, this would extract from PMTiles or load from a separate endpoint
        this.features = [
            { id: 'feat-1', name: 'Sample Fire Area A', fire_date: '2023-09-15' },
            { id: 'feat-2', name: 'Sample Fire Area B', fire_date: '2023-10-02' },
            { id: 'feat-3', name: 'Sample Fire Point', fire_date: '2023-11-20' }
        ];
        
        this.updateFeatureList();
    }
    
    async loadSTACCollection() {
        try {
            this.updateStatus('Loading STAC collection...', 'loading');
            
            const collectionUrl = `${this.config.stacBasePath}collection.json`;
            const response = await fetch(collectionUrl);
            
            if (!response.ok) {
                throw new Error(`Failed to load collection: ${response.status}`);
            }
            
            const collection = await response.json();
            console.log('Loaded STAC Collection:', collection);
            
            // Extract temporal information for date slider
            await this.loadSTACItems();
            
        } catch (error) {
            console.error('STAC collection loading failed:', error);
            this.updateStatus('⚠️ STAC collection not found (using demo features)', 'error');
            this.setupDemoDateSlider();
        }
    }
    
    async loadSTACItems() {
        try {
            // In a real implementation, we'd get item links from the collection
            // For now, attempt to load based on feature IDs
            this.items = [];
            this.dates = [];
            
            for (const feature of this.features) {
                // Try to find corresponding STAC items
                // This is a simplified approach - real implementation would use collection links
                const itemId = `item-${feature.id}`;
                try {
                    const itemUrl = `${this.config.stacBasePath}items/${itemId}.json`;
                    const response = await fetch(itemUrl);
                    if (response.ok) {
                        const item = await response.json();
                        this.items.push(item);
                        
                        // Extract datetime
                        if (item.properties.datetime) {
                            this.dates.push({
                                date: new Date(item.properties.datetime),
                                itemId: item.id,
                                featureId: feature.id
                            });
                        }
                    }
                } catch (error) {
                    console.warn(`Could not load item for feature ${feature.id}`);
                }
            }
            
            if (this.dates.length > 0) {
                this.dates.sort((a, b) => a.date - b.date);
                this.setupDateSlider();
            } else {
                this.setupDemoDateSlider();
            }
            
        } catch (error) {
            console.error('STAC items loading failed:', error);
            this.setupDemoDateSlider();
        }
    }
    
    setupDateSlider() {
        const slider = document.getElementById('dateSlider');
        slider.max = this.dates.length - 1;
        slider.value = 0;
        
        slider.addEventListener('input', (e) => {
            this.currentDateIndex = parseInt(e.target.value);
            this.updateDateDisplay();
            this.filterFeaturesByDate();
        });
        
        this.updateDateDisplay();
    }
    
    setupDemoDateSlider() {
        // Setup demo date slider with sample dates
        this.dates = [
            { date: new Date('2023-09-15'), label: 'Sept 15, 2023' },
            { date: new Date('2023-10-02'), label: 'Oct 2, 2023' },
            { date: new Date('2023-11-20'), label: 'Nov 20, 2023' }
        ];
        
        const slider = document.getElementById('dateSlider');
        slider.max = this.dates.length - 1;
        slider.value = 0;
        
        slider.addEventListener('input', (e) => {
            this.currentDateIndex = parseInt(e.target.value);
            this.updateDateDisplay();
        });
        
        this.updateDateDisplay();
    }
    
    updateDateDisplay() {
        const dateDisplay = document.getElementById('dateDisplay');
        if (this.dates.length > 0) {
            const currentDate = this.dates[this.currentDateIndex];
            dateDisplay.textContent = currentDate.label || currentDate.date.toLocaleDateString();
        }
    }
    
    filterFeaturesByDate() {
        // In a full implementation, this would filter the PMTiles layer
        // For now, just update the UI to show current date context
        console.log(`Filtering features for date index: ${this.currentDateIndex}`);
    }
    
    updateFeatureList() {
        const featureList = document.getElementById('featureList');
        const featureCount = document.getElementById('featureCount');
        
        featureCount.textContent = this.features.length;
        
        if (this.features.length === 0) {
            featureList.innerHTML = '<div class="status">No features found</div>';
            return;
        }
        
        const listHTML = this.features.map(feature => `
            <div class="feature-item" data-feature-id="${feature.id}">
                <strong>${feature.name || feature.id}</strong>
                ${feature.fire_date ? `<br><small>📅 ${feature.fire_date}</small>` : ''}
            </div>
        `).join('');
        
        featureList.innerHTML = listHTML;
        
        // Add click handlers
        featureList.querySelectorAll('.feature-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const featureId = e.currentTarget.dataset.featureId;
                this.selectFeature(featureId);
            });
        });
    }
    
    selectFeature(featureId) {
        // Update UI selection
        document.querySelectorAll('.feature-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const selectedItem = document.querySelector(`[data-feature-id="${featureId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }
        
        this.selectedFeature = featureId;
        
        // Try to load and display raster for this feature
        this.loadFeatureRaster(featureId);
    }
    
    async loadFeatureRaster(featureId) {
        try {
            this.updateStatus(`Loading raster for ${featureId}...`, 'loading');
            
            // Check if TiTiler is configured
            if (!this.config.tilerBaseUrl) {
                this.updateStatus('⚠️ No TiTiler configured - raster display not available', 'error');
                return;
            }
            
            // Find corresponding STAC item
            const item = this.items.find(item => 
                item.properties && item.properties.feature_id === featureId
            );
            
            if (!item) {
                this.updateStatus(`No STAC item found for feature ${featureId}`, 'error');
                return;
            }
            
            // Find primary COG asset
            const primaryAssets = Object.entries(item.assets || {}).filter(([key, asset]) => 
                asset.roles && asset.roles.includes('primary') && asset.roles.includes('data')
            );
            
            if (primaryAssets.length === 0) {
                this.updateStatus(`No primary COG asset found for ${featureId}`, 'error');
                return;
            }
            
            const [assetKey, primaryAsset] = primaryAssets[0];
            
            // Derive TiTiler URL from S3 COG HREF
            const tilerUrl = this.buildTiTilerUrl(primaryAsset.href);
            
            // Remove existing raster layer for this feature
            if (this.rasterLayers.has(featureId)) {
                this.map.removeLayer(this.rasterLayers.get(featureId));
            }
            
            // Add new raster layer
            const rasterLayer = L.tileLayer(tilerUrl, {
                attribution: `Raster: ${item.id}`,
                opacity: 0.7
            });
            
            rasterLayer.addTo(this.map);
            this.rasterLayers.set(featureId, rasterLayer);
            
            this.updateStatus(`✅ Loaded raster for ${featureId}`, 'success');
            
        } catch (error) {
            console.error('Raster loading failed:', error);
            this.updateStatus(`❌ Failed to load raster: ${error.message}`, 'error');
        }
    }
    
    buildTiTilerUrl(cogHref) {
        // Convert S3 COG HREF to TiTiler tile URL using COG endpoint
        // Uses WebMercatorQuad tile matrix set for web maps
        
        const encodedUrl = encodeURIComponent(cogHref);
        return `${this.config.tilerBaseUrl}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?url=${encodedUrl}&format=webp`;
    }
    
    handleMapClick(e) {
        // Handle clicks on PMTiles features
        console.log('Map clicked at:', e.latlng);
        
        // In a real implementation, we'd query the PMTiles layer for features at this point
        // and then call selectFeature() with the clicked feature ID
    }
    
    updateStatus(message, type = 'info') {
        const status = document.getElementById('status');
        status.textContent = message;
        status.className = `status ${type}`;
        
        console.log(`Status (${type}): ${message}`);
    }
    
    // Configuration management
    static loadConfig() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Support CloudFront-based deployments
        const jobId = urlParams.get('job_id') || urlParams.get('jobId');
        const cloudfrontUrl = urlParams.get('cloudfront') || urlParams.get('tiler');
        
        // Build paths based on job ID and CloudFront URL if provided
        let pmtilesPath = '../pmtiles/features.pmtiles';
        let stacBasePath = '../stac/';
        
        if (cloudfrontUrl && jobId) {
            // Use CloudFront URLs for deployed infrastructure
            pmtilesPath = `${cloudfrontUrl}/jobs/${jobId}/pmtiles/features.pmtiles`;
            stacBasePath = `${cloudfrontUrl}/jobs/${jobId}/stac/`;
        } else if (jobId) {
            // Use relative paths with specific job ID
            pmtilesPath = `../jobs/${jobId}/pmtiles/features.pmtiles`;
            stacBasePath = `../jobs/${jobId}/stac/`;
        }
        
        return {
            pmtilesPath: urlParams.get('pmtiles') || pmtilesPath,
            stacBasePath: urlParams.get('stac') || stacBasePath,
            tilerBaseUrl: cloudfrontUrl || urlParams.get('tiler') || null, // No default tiler - must be specified
            jobId: jobId
        };
    }
}

// Initialize the map when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Override config from URL parameters if provided
    const map = new GeoExhibitMap();
    map.config = { ...map.config, ...GeoExhibitMap.loadConfig() };
    
    // Global reference for debugging
    window.geoExhibitMap = map;
    
    console.log('GeoExhibit Map initialized');
    console.log('Configuration:', map.config);
});