import { fetchJSON, getColorByStatus, getOverallStatus, getRegionName,
        formatNotification, updateRegionStatus } from './utils.js';
import { ReconnectingWebSocket } from './ws.js';
import { showNotification } from './notifications.js';

export async function initMap() {
    return new Promise(async (resolve, reject) => {
        try {
            const map = new maplibregl.Map({
            container: 'map',
            style: 'https://api.maptiler.com/maps/019a9862-79a9-7410-a60e-d9677092aeb9/style.json?key=YZumvdEmv8k1susiNBxS',
            center: [37.6, 55.75],
            zoom: 4
            });

            const REGION_STATUS = {
            "Москва": {AIR: "", ROCKET: "", UAV: "", UB: ""}
            };

            const nameMap = {
            "Адыгея": "Республика Адыгея",
            "Алтай": "Республика Алтай",
            "Башкортостан": "Республика Башкортостан",
            "Бурятия": "Республика Бурятия",
            "Дагестан": "Республика Дагестан",
            "Ингушетия": "Республика Ингушетия",
            "Кабардино-Балкарская республика": "Кабардино-Балкарская Республика",
            "Республика Калмыкия": "Республика Калмыкия",
            "Карачаево-Черкесская республика": "Карачаево-Черкесская Республика",
            "Республика Карелия": "Республика Карелия",
            "Республика Коми": "Республика Коми",
            "Марий Эл": "Республика Марий Эл",
            "Республика Мордовия": "Республика Мордовия",
            "Республика Саха (Якутия)": "Республика Саха (Якутия)",
            "Северная Осетия - Алания": "Республика Северная Осетия (Алания)",
            "Татарстан": "Республика Татарстан",
            "Тыва": "Республика Тыва",
            "Удмуртская республика": "Удмуртская Республика",
            "Республика Хакасия": "Республика Хакасия",
            "Чеченская республика": "Чеченская Республика",
            "Чувашия": "Чувашская Республика",
            "Алтайский край": "Алтайский край",
            "Забайкальский край": "Забайкальский край",
            "Камчатский край": "Камчатский край",
            "Краснодарский край": "Краснодарский край",
            "Красноярский край": "Красноярский край",
            "Пермский край": "Пермский край",
            "Приморский край": "Приморский край",
            "Ставропольский край": "Ставропольский край",
            "Хабаровский край": "Хабаровский край",
            "Амурская область": "Амурская область",
            "Архангельская область": "Архангельская область",
            "Астраханская область": "Астраханская область",
            "Белгородская область": "Белгородская область",
            "Брянская область": "Брянская область",
            "Владимирская область": "Владимирская область",
            "Волгоградская область": "Волгоградская область",
            "Вологодская область": "Вологодская область",
            "Воронежская область": "Воронежская область",
            "Ивановская область": "Ивановская область",
            "Иркутская область": "Иркутская область",
            "Калининградская область": "Калининградская область",
            "Калужская область": "Калужская область",
            "Кемеровская область": "Кемеровская область",
            "Кировская область": "Кировская область",
            "Костромская область": "Костромская область",
            "Курганская область": "Курганская область",
            "Курская область": "Курская область",
            "Ленинградская область": "Ленинградская область",
            "Липецкая область": "Липецкая область",
            "Магаданская область": "Магаданская область",
            "Московская область": "Московская область",
            "Мурманская область": "Мурманская область",
            "Нижегородская область": "Нижегородская область",
            "Новгородская область": "Новгородская область",
            "Новосибирская область": "Новосибирская область",
            "Омская область": "Омская область",
            "Оренбургская область": "Оренбургская область",
            "Орловская область": "Орловская область",
            "Пензенская область": "Пензенская область",
            "Псковская область": "Псковская область",
            "Ростовская область": "Ростовская область",
            "Рязанская область": "Рязанская область",
            "Самарская область": "Самарская область",
            "Саратовская область": "Саратовская область",
            "Сахалинская область": "Сахалинская область",
            "Свердловская область": "Свердловская область",
            "Смоленская область": "Смоленская область",
            "Тамбовская область": "Тамбовская область",
            "Тверская область": "Тверская область",
            "Томская область": "Томская область",
            "Тульская область": "Тульская область",
            "Тюменская область": "Тюменская область",
            "Ульяновская область": "Ульяновская область",
            "Челябинская область": "Челябинская область",
            "Ярославская область": "Ярославская область",
            "Москва": "Москва",
            "Санкт-Петербург": "Санкт-Петербург",
            "Еврейская автономная область": "Еврейская автономная область",
            "Ненецкий автономный округ": "Ненецкий автономный округ",
            "Ханты-Мансийский автономный округ - Югра": "Ханты-Мансийский автономный округ",
            "Чукотский автономный округ": "Чукотский автономный округ",
            "Ямало-Ненецкий автономный округ": "Ямало-Ненецкий автономный округ",
            "Автономна Республіка Крим": "Республика Крым",
            "Севастополь": "Севастополь",
            "Донецька область": "Донецкая Народная Республика",
            "Луганська область": "Луганская Народная Республика",
            "Запорізька область": "Запорожская область",
            "Херсонська область": "Херсонская область",
            "м. Севастополь": "Севастополь"
            };

            const allowedUB = [
                "Донецкая Народная Республика",
                "Запорожская область",
                "Херсонская область",
                "Республика Крым",
                "Севастополь",
                "Краснодарский край",
                "Ростовская область"
            ]

            let geoRu = null;
            let geoUa = null;

            try {
            geoRu = await fetchJSON('https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/russia.geojson');
            } catch (err) {
            console.error("[INIT] Error while loading Russia:", err);
            }

            try {
            geoUa = await fetchJSON('https://raw.githubusercontent.com/verprog/Geojson-region-ukraine/master/ukraine.geojson');
            } catch (err) {
            console.error("[INIT] Error while loading Ukraine:", err);
            }

            const geoUAallowedRegions = new Set([
            "Республика Крым",
            "Севастополь",
            "Донецкая Народная Республика",
            "Луганская Народная Республика",
            "Запорожская область",
            "Херсонская область",
            "Севастополь"
            ]);

            const geoUAfeatures = geoUa?.features.filter(feat => {
            const nm = nameMap[feat.properties.name] || feat.properties.name;
            return geoUAallowedRegions.has(nm);
            });

            const combined = {
            type: "FeatureCollection",
            features: [
                ...(geoRu?.features || []),
                ...(geoUAfeatures || [])
            ]
            };

            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const ws = new ReconnectingWebSocket(`${protocol}//${window.location.host}/ws`, {
            baseDelay: 10000,
            maxDelay: 15000,
            maxAttempts: 0,
            debug: false
            });

            ws.onopen = () => {
                console.log("[WS] Connected");
            };

            ws.onmessage = (msg) => {
            try {
                const data = JSON.parse(msg.data);
                console.log(`[WS] Message (type: ${data.type}):`, data);

                if (data.type === "region_update") {
                    updateRegionStatus(
                        data.data.region,
                        data.data.statuses,
                        REGION_STATUS,
                        map,
                        nameMap,
                        showNotification
                    );
                }

                if (data.type === "snapshot") {
                for (const [reg, statuses] of Object.entries(data.data)) {
                    for (const status in statuses) {
                        if (REGION_STATUS[reg] === undefined) {
                            REGION_STATUS[reg] = {AIR: "", ROCKET: "", UAV: "", UB: ""};
                        }
                        REGION_STATUS[reg][status] = statuses[status];
                    }
                }
                updateRegionStatus(null, null, REGION_STATUS, map, nameMap, showNotification);
                }
            } catch (e) {
                console.error("WS error:", e);
            }
            };

            ws.onerror = (err) => console.error("[WS] Error:", err);
            ws.onclose = () => console.warn("[WS] Closed");

            map.on('load', () => {
            map.addSource('regions', {
                type: 'geojson',
                data: combined
            });

            const expr = ['match', ['get', 'name']];
            for (const feat of combined.features) {
                const nm = getRegionName(feat.properties);
                const key = nameMap[nm] || nm;
                if (REGION_STATUS[key] !== undefined) {
                    expr.push(nm, getColorByStatus(getOverallStatus(REGION_STATUS[key])));
                }
            }
            expr.push(getColorByStatus(undefined));

            map.addLayer({
                id: 'regions-fill',
                type: 'fill',
                source: 'regions',
                paint: {
                'fill-color': expr,
                'fill-opacity': 0.6
                }
            });

            map.addLayer({
                id: 'regions-border',
                type: 'line',
                source: 'regions',
                paint: {
                'line-color': '#333',
                'line-width': 0.8
                }
            });

            map.on('click', 'regions-fill', (e) => {
                const props = e.features[0].properties;
                const nm = props.name;
                const key = nameMap[nm] || nm;
                let text = `<b><div style="font-size:16px; line-height:1; margin:0; text-align: center; margin-bottom: 5px;">${key}</div></b>`;
                for (const type in REGION_STATUS[key]) { 
                    if (!allowedUB.includes(key) && type === "UB") continue;
                    const color = getColorByStatus(REGION_STATUS[key][type]);
                    text += `${formatNotification(type)}: <span style="color:${color}; font-size:11px;"><b>${formatNotification(REGION_STATUS[key][type])}</b></span><br>`;
                }
                new maplibregl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(`${text}`)
                .addTo(map);
            });

            map.on('mouseenter', 'regions-fill', () => map.getCanvas().style.cursor = 'pointer');
            map.on('mouseleave', 'regions-fill', () => map.getCanvas().style.cursor = '');

            resolve(map);

            });
        } catch (e) {
            reject(e);
        }
    });
}
