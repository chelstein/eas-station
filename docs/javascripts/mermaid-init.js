/**
 * Mermaid diagram initialization for EAS Station MkDocs site.
 *
 * This script configures Mermaid.js after it has been loaded from CDN.
 * It is referenced in mkdocs.yml under extra_javascript and runs after
 * the Mermaid library script so diagrams render in both light and dark modes.
 */
document.addEventListener('DOMContentLoaded', function () {
    if (typeof mermaid !== 'undefined') {
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            themeVariables: {
                primaryColor: '#3b82f6',
                primaryTextColor: '#0f172a',
                primaryBorderColor: '#1e40af',
                lineColor: '#475569',
                secondaryColor: '#e2e8f0',
                tertiaryColor: '#f8fafc'
            },
            flowchart: {
                htmlLabels: true,
                curve: 'linear'
            },
            sequence: {
                showSequenceNumbers: false
            },
            er: {
                useMaxWidth: true
            }
        });
    }
});
