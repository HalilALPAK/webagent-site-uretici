@props(['name' => 'spark'])
{{-- Modüllere göre küçük çizgi ikonlar (tek set, 1.6 kalınlık) --}}
@php
    $paths = [
        'home' => '<path d="M4 11 12 4l8 7"/><path d="M6 10v9h12v-9"/>',
        'calendar' => '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
        'photo' => '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m5 17 5-5 4 4 2-2 3 3"/>',
        'news' => '<rect x="3" y="4" width="14" height="16" rx="2"/><path d="M7 8h6M7 12h6M7 16h4M17 9h3v9a2 2 0 0 1-3 0z"/>',
        'question' => '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3 2.4V14"/><path d="M12 17.2v.2"/>',
        'chat' => '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z"/>',
        'users' => '<circle cx="9" cy="9" r="3"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 7a3 3 0 0 1 0 6M17.5 20a6 6 0 0 0-2-4.2"/>',
        'tag' => '<path d="m3 12 8.5-8.5H20V12l-8.5 8.5z"/><circle cx="16" cy="8" r="1.4"/>',
        'bag' => '<path d="M6 8h12l1 12H5z"/><path d="M9 8a3 3 0 0 1 6 0"/>',
        'pin' => '<path d="M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11z"/><circle cx="12" cy="10" r="2.4"/>',
        'ticket' => '<path d="M4 9V7h16v2a2.5 2.5 0 0 0 0 6v2H4v-2a2.5 2.5 0 0 0 0-6z"/><path d="M13 7v10" stroke-dasharray="2 3"/>',
        'sparkles' => '<path d="m12 4 1.6 4.4L18 10l-4.4 1.6L12 16l-1.6-4.4L6 10l4.4-1.6z"/><path d="M18 16.5 18.8 18l1.5.8-1.5.7L18 21l-.8-1.5-1.5-.7 1.5-.8z"/>',
        'star' => '<path d="m12 4 2.4 5 5.6.8-4 3.9 1 5.5-5-2.7-5 2.7 1-5.5-4-3.9 5.6-.8z"/>',
        'briefcase' => '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5h6v2M3 12h18"/>',
        'doc' => '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
        'spark' => '<circle cx="12" cy="12" r="8"/><path d="M12 8v8M8 12h8"/>',
    ];
@endphp
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"
     stroke-linejoin="round" aria-hidden="true" class="ico">{!! $paths[$name] ?? $paths['spark'] !!}</svg>
