export async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) {
    throw new Error(`HTTP ${resp.status} for URL ${url}`);
    }
    return await resp.json();
}

export function getColorByStatus(status) {
    switch (status) {
    case "HD": return "#bf1717";
    case "MD": return "#d1ab15";
    case "AC": return "#48ad23";
    default: return "#2e86d8";
    }
}

export function getRegionName(props) {
    return props.name;
}

export function updateRegionStatus(
    region,
    newStatuses,
    REGION_STATUS,
    map,
    nameMap,
    notify
) {
    if (region && newStatuses) {
        for (const statusKey in newStatuses) {
            const newValue = newStatuses[statusKey];
            if (REGION_STATUS[region][statusKey] !== newValue) {
                REGION_STATUS[region][statusKey] = newValue;
                if (typeof notify === 'function') {
                    notify(
                        `<b>${region}</b>`,
                        `<b>${formatNotification(statusKey)}</b>`,
                        `${newValue}`
                    );
                }
            }
        }
    }

    const src = map.getSource('regions');
    if (!src || !src._data) {
        console.warn('[utils] Source is not ready yet');
        return;
    }

    const expr = ['match', ['get', 'name']];

    for (const feat of src._data.features) {
        const nm  = feat.properties.name;
        const key = nameMap[nm] || nm;
        const overall = getOverallStatus(REGION_STATUS[key]);
        expr.push(nm, getColorByStatus(overall));
    }

    expr.push(getColorByStatus(undefined));

    map.setPaintProperty('regions-fill', 'fill-color', expr);
}

export function getOverallStatus(statuses) {
    if (!statuses) return 'Не задан';
    if (Object.values(statuses).includes('HD')) return 'HD';
    if (Object.values(statuses).includes('MD')) return 'MD';
    if (Object.values(statuses).includes('AC')) return 'AC';
    return 'Не задан';
}

export function formatNotification(status) {
    switch (status) {
        case 'AIR':   return 'Угроза воздушной атаки';
        case 'ROCKET':return 'Угроза ракетной атаки';
        case 'UAV':   return 'Угроза атаки БПЛА';
        case 'UB':    return 'Угроза атаки БЭК';
        case 'AC':    return 'Отбой';
        case 'MD':    return 'Средняя';
        case 'HD':    return 'Высокая';
        default:      return 'Не задан';
    }
}

export function getIconByType(type) {
    switch (type) {
        case 'AC': return 'done_outline';
        case 'MD': return 'warning';
        case 'HD': return 'e911_emergency';
        default:   return 'notifications';
    }
}