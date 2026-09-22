@php
    use App\Support\SiteConfig as S;
    $num = collect($meta['fields'])->first(fn ($f) => in_array($f['type'], ['int', 'float', 'price']));
    $body = S::bodyField($meta);
@endphp
<div class="stats">
    @foreach ($records as $r)
        <div class="stat">
            <strong>{{ $num ? S::format($r, $num) : S::title($r, $meta) }}</strong>
            <span>{{ $num ? S::title($r, $meta) : S::excerpt($body ? $r->{$body['name']} : '', 80) }}</span>
        </div>
    @endforeach
</div>
