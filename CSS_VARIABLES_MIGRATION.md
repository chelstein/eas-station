# CSS Variables Migration - Stats Dashboard

## Overview
This document describes the migration of hardcoded colors to CSS variables in the statistics dashboard templates.

## Date
December 2024

## Files Modified
1. `templates/stats/_scripts.html` - Chart.js configuration and color management
2. `templates/stats/_styles.html` - CSS styling for dashboard components

## Changes Summary

### JavaScript (_scripts.html)

#### New Helper Functions

```javascript
// Get CSS variable value with fallback
function getCSSVar(varName, fallback = '#212529') {
    const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
    return value || fallback;
}

// Convert hex color to RGB object for rgba() creation
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : { r: 102, g: 126, b: 234 };
}
```

#### Gradient Palette Refactor

**Before:**
```javascript
const GRADIENT_PALETTES = {
    primary: ['#667eea', '#764ba2'],
    success: ['#11998e', '#38ef7d'],
    // ... more hardcoded colors
};
```

**After:**
```javascript
const GRADIENT_PALETTES = {
    primary: [getCSSVar('--chart-primary-start', '#667eea'), getCSSVar('--chart-primary-end', '#764ba2')],
    success: [getCSSVar('--chart-success-start', '#11998e'), getCSSVar('--chart-success-end', '#38ef7d')],
    // ... using CSS variables with fallbacks
};
```

#### Chart Functions Updated

All chart creation functions now use CSS variables for:
- Border colors
- Background gradients
- Point colors
- Text colors
- Grid lines

Example from `createHourlyLineChart()`:
```javascript
const dangerStartRgb = hexToRgb(getCSSVar('--chart-danger-start', '#eb3349'));
const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
gradient.addColorStop(0, `rgba(${dangerStartRgb.r}, ${dangerStartRgb.g}, ${dangerStartRgb.b}, 0.5)`);
```

### CSS (_styles.html)

#### Gradient Variable Updates

**Before:**
```css
--gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

**After:**
```css
--gradient-primary: linear-gradient(135deg, var(--chart-primary-start) 0%, var(--chart-primary-end) 100%);
```

#### Color-Mix for Transparency

**Before:**
```css
box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
```

**After:**
```css
box-shadow: 0 0 0 3px color-mix(in srgb, var(--chart-primary-start) 20%, transparent);
```

## CSS Variables Used

All defined in `static/css/styles.css`:

### Chart Colors
- `--chart-primary-start` / `--chart-primary-end`
- `--chart-success-start` / `--chart-success-end`
- `--chart-danger-start` / `--chart-danger-end`
- `--chart-warning-start` / `--chart-warning-end`
- `--chart-info-start` / `--chart-info-end`

### Chart Elements
- `--chart-grid` - Grid line color
- `--chart-text` - Chart text color

### Theme Variables (inherited)
- `--text-color`
- `--text-muted`
- `--surface-color`
- `--border-color`

## Benefits

1. **Theme Consistency**: Charts automatically match the current theme
2. **Dark Mode Support**: Charts adapt to light/dark theme preferences
3. **Centralized Management**: All colors defined in one location
4. **Easy Customization**: Override CSS variables for custom color schemes
5. **Maintainability**: Single source of truth for dashboard colors

## Browser Compatibility

- CSS Variables: All modern browsers (IE11 not supported)
- `color-mix()`: Modern browsers (Chrome 111+, Firefox 113+, Safari 16.2+)
  - Fallback colors provided for older browsers

## Testing Performed

✓ Syntax validation (balanced braces, brackets, parentheses)
✓ CSS variable reference count: 27 chart-specific variables
✓ JavaScript function calls: 54 getCSSVar(), 17 hexToRgb()
✓ Zero hardcoded color arrays remaining

## Migration Statistics

- **_scripts.html**: 179 lines changed
- **_styles.html**: 38 lines changed
- **getCSSVar() calls**: 54
- **hexToRgb() calls**: 17
- **Chart CSS variables**: 27 references
- **color-mix() usage**: 7 instances

## Maintenance Notes

### Adding New Charts

When creating new charts, use:
```javascript
const borderColor = getCSSVar('--chart-primary-start', '#667eea');
const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
const rgb = hexToRgb(getCSSVar('--chart-primary-start', '#667eea'));
gradient.addColorStop(0, `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.5)`);
```

### Adding New Themes

1. Define chart color variables in theme's CSS
2. No changes needed in JavaScript - colors auto-update
3. Test all chart types in new theme

### Troubleshooting

**Charts showing wrong colors?**
- Check that CSS variables are defined in active theme
- Verify browser supports CSS custom properties
- Check console for JavaScript errors

**Gradients not appearing?**
- Ensure canvas context is available before creating gradients
- Verify hexToRgb() returns valid RGB values
- Check that CSS variables resolve to valid colors

## Future Enhancements

- [ ] Add more chart color variables for additional customization
- [ ] Consider CSS variable fallbacks for older browsers
- [ ] Add user-configurable color picker in settings
- [ ] Export/import custom color themes

## Related Files

- `static/css/styles.css` - CSS variable definitions
- `templates/stats.html` - Main stats dashboard template
- `webapp/stats/routes.py` - Stats data endpoints

## References

- [MDN: CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [MDN: color-mix()](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value/color-mix)
- [Chart.js Documentation](https://www.chartjs.org/docs/latest/)
