@php use App\Support\SiteConfig as S; @endphp
@if (! $meta['image_field'])
    @include('site.sections.cards')
@else
    <div class="gallery">
        @foreach ($records as $r)
            @php $img = S::image($r, $meta); @endphp
            <a href="{{ url($meta['name'].'/'.$r->getKey()) }}" @class(['gallery-item', 'reveal', 'gallery-tall' => $loop->iteration % 3 === 1])>
                @if ($img)
                    <img src="{{ $img }}" alt="{{ S::title($r, $meta) }}" loading="lazy">
                @else
                    <div class="media-fallback"><span>{{ S::initial(S::title($r, $meta)) }}</span></div>
                @endif
                <span class="gallery-caption">{{ S::title($r, $meta) }}</span>
            </a>
        @endforeach
    </div>
@endif
