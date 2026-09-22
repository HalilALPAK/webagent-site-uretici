@if ($paginator->hasPages())
    <nav class="pagination" aria-label="Sayfalar">
        @if ($paginator->onFirstPage())
            <span class="disabled">←</span>
        @else
            <a href="{{ $paginator->previousPageUrl() }}" rel="prev" aria-label="Önceki">←</a>
        @endif
        @foreach ($elements as $element)
            @if (is_string($element))
                <span class="disabled">{{ $element }}</span>
            @endif
            @if (is_array($element))
                @foreach ($element as $page => $url)
                    @if ($page == $paginator->currentPage())
                        <span class="current" aria-current="page">{{ $page }}</span>
                    @else
                        <a href="{{ $url }}">{{ $page }}</a>
                    @endif
                @endforeach
            @endif
        @endforeach
        @if ($paginator->hasMorePages())
            <a href="{{ $paginator->nextPageUrl() }}" rel="next" aria-label="Sonraki">→</a>
        @else
            <span class="disabled">→</span>
        @endif
    </nav>
@endif
