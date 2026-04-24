/**
 * EAS Station - Lightning Theme Bolt Renderer
 *
 * When the "lightning" theme is active, this module injects an overlay of
 * procedurally generated lightning bolts with:
 *   - Branching forks that recurse to shallow depth
 *   - Tapered stroke widths along each segment
 *   - Independent timing for left and right bolts
 *   - A fresh randomized path on every animation iteration
 *
 * The overlay is created/destroyed in response to the `theme-changed` event
 * dispatched by theme.js.
 */
(function() {
    'use strict';

    const LIGHTNING = 'lightning';
    const SVG_NS = 'http://www.w3.org/2000/svg';

    let overlay = null;
    let leftBolt = null;
    let rightBolt = null;

    function rand(min, max) {
        return Math.random() * (max - min) + min;
    }

    function chance(p) {
        return Math.random() < p;
    }

    /* Trunk: a primary top-to-bottom bolt drifting with controlled jitter. */
    function generateTrunk(startX, startY, endY, segments, drift) {
        const points = [{ x: startX, y: startY }];
        const stepY = (endY - startY) / segments;
        let x = startX;
        for (let i = 1; i < segments; i++) {
            x += rand(-drift, drift);
            const y = startY + stepY * i + rand(-stepY * 0.25, stepY * 0.25);
            points.push({ x, y });
        }
        points.push({ x: x + rand(-drift, drift), y: endY });
        return points;
    }

    /* Branches: spawn from random trunk vertices and fork off at an angle.
       Recurse so each branch can sprout sub-branches at reduced chance. */
    function generateBranches(parent, spawnChance, depth, baseWidth, sideHint) {
        const out = [];
        if (depth <= 0) return out;
        for (let i = 1; i < parent.length - 1; i++) {
            if (!chance(spawnChance)) continue;
            const origin = parent[i];
            const direction = sideHint !== undefined
                ? sideHint
                : (chance(0.5) ? -1 : 1);
            const length = rand(60, 180);
            const segments = Math.floor(rand(3, 7));
            const step = length / segments;
            const angle = rand(0.7, 1.4); // radians off vertical
            const branch = [{ x: origin.x, y: origin.y }];
            let cx = origin.x;
            let cy = origin.y;
            for (let j = 1; j <= segments; j++) {
                const lateral = Math.sin(angle + rand(-0.35, 0.35)) * step * direction;
                const descent = Math.cos(angle) * step * 0.7 + rand(0, step * 0.3);
                cx += lateral;
                cy += descent;
                branch.push({ x: cx, y: cy });
            }
            out.push({ points: branch, width: baseWidth });
            if (depth > 1 && chance(spawnChance * 0.55)) {
                out.push(...generateBranches(
                    branch,
                    spawnChance * 0.5,
                    depth - 1,
                    baseWidth * 0.6,
                    direction
                ));
            }
        }
        return out;
    }

    function appendSegment(group, p1, p2, width, color, opacity) {
        const seg = document.createElementNS(SVG_NS, 'path');
        seg.setAttribute('d', `M${p1.x.toFixed(1)} ${p1.y.toFixed(1)} L${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`);
        seg.setAttribute('stroke', color);
        seg.setAttribute('stroke-width', width.toFixed(2));
        seg.setAttribute('stroke-linecap', 'round');
        seg.setAttribute('fill', 'none');
        seg.setAttribute('opacity', opacity.toFixed(2));
        group.appendChild(seg);
    }

    /* Taper: stroke width shrinks from root to tip.
       Three concentric strokes create a halo / glow / core. */
    function renderPolyline(group, points, baseWidth, taper) {
        const total = points.length - 1;
        if (total <= 0) return;
        for (let i = 0; i < total; i++) {
            const t = i / total;
            const width = baseWidth * (1 - t * taper);
            appendSegment(group, points[i], points[i + 1], width * 3.0, '#7fd7ff', 0.35);
            appendSegment(group, points[i], points[i + 1], width * 1.8, '#d8f0ff', 0.55);
            appendSegment(group, points[i], points[i + 1], width, '#ffffff', 0.98);
        }
    }

    function buildBolt(svg, side) {
        while (svg.firstChild) svg.removeChild(svg.firstChild);
        const rootX = side === 'left' ? rand(60, 260) : rand(940, 1140);
        const endY = rand(720, 820);
        const segments = Math.floor(rand(11, 17));
        const drift = rand(30, 55);
        const trunk = generateTrunk(rootX, -20, endY, segments, drift);
        // Branches skew outward from the screen center
        const sideHint = side === 'left' ? 1 : -1;
        const branches = generateBranches(trunk, 0.38, 2, 1.4, sideHint);

        const group = document.createElementNS(SVG_NS, 'g');
        renderPolyline(group, trunk, 1.8, 0.6);
        branches.forEach(b => renderPolyline(group, b.points, b.width, 0.55));
        svg.appendChild(group);
    }

    function makeBoltSvg(side) {
        const svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('viewBox', '0 0 1200 800');
        svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
        svg.setAttribute('aria-hidden', 'true');
        svg.classList.add('lightning-bolt', `lightning-bolt-${side}`);
        return svg;
    }

    function mount() {
        if (overlay) return;
        overlay = document.createElement('div');
        overlay.id = 'lightning-overlay';
        overlay.setAttribute('aria-hidden', 'true');
        leftBolt = makeBoltSvg('left');
        rightBolt = makeBoltSvg('right');
        overlay.appendChild(leftBolt);
        overlay.appendChild(rightBolt);
        document.body.appendChild(overlay);
        buildBolt(leftBolt, 'left');
        buildBolt(rightBolt, 'right');
        // Re-randomize each bolt when its CSS animation loops
        leftBolt.addEventListener('animationiteration', () => buildBolt(leftBolt, 'left'));
        rightBolt.addEventListener('animationiteration', () => buildBolt(rightBolt, 'right'));
    }

    function unmount() {
        if (!overlay) return;
        overlay.remove();
        overlay = null;
        leftBolt = null;
        rightBolt = null;
    }

    function sync(theme) {
        if (theme === LIGHTNING) mount();
        else unmount();
    }

    window.addEventListener('theme-changed', (e) => sync(e.detail && e.detail.theme));

    function init() {
        sync(document.documentElement.getAttribute('data-theme'));
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
