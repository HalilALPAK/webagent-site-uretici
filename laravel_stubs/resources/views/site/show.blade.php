@extends('site.layout')
@php
    use App\Support\SiteConfig as S;
    $title = S::title($record, $meta);
    $body = S::bodyField($meta);
    $price = S::priceField($meta);
    $facts = collect($meta['fields'])->filter(fn ($f) => $f['name'] !== $meta['title_field']
        && ! in_array($f['type'], ['image', 'text', 'richtext', 'price']));
    $longs = collect($meta['fields'])->whereIn('type', ['text', 'richtext']);
    $t = S::all()['theme'];
@endphp
@section('title', $title.' — '.S::get('site_name'))
@section('description', S::excerpt($body ? $record->{$body['name']} : S::get('meta_description'), 155))

@section('content')
    <section class="detail-top">
        <div class="container">
            <nav class="breadcrumb" aria-label="Konum">
                <a href="{{ url('/') }}">Ana sayfa</a> <span>/</span>
                <a href="{{ url('/'.$meta['name']) }}">{{ $meta['label_plural'] }}</a> <span>/</span> {{ $title }}
            </nav>
            <div @class(['detail-grid', 'no-media' => ! $meta['image_field']])>
                @if ($meta['image_field'])
                    @include('site.partials.media', ['r' => $record, 'meta' => $meta, 'ratio' => 'ratio-4-3 detail-media'])
                @endif
                <div class="detail-info">
                    <span class="eyebrow">{{ $meta['label'] }}</span>
                    <h1>{{ $title }}</h1>
                    @if ($facts->isNotEmpty())
                        <dl class="facts">
                            @foreach ($facts as $f)
                                @if (($v = S::format($record, $f)) !== null)
                                    <div>
                                        <dt>{{ $f['label'] }}</dt>
                                        <dd>
                                            @if ($f['type'] === 'url')<a href="{{ $v }}" target="_blank" rel="noopener nofollow">{{ parse_url($v, PHP_URL_HOST) ?: $v }}</a>
                                            @elseif ($f['type'] === 'email')<a href="mailto:{{ $v }}">{{ $v }}</a>
                                            @elseif ($f['type'] === 'phone')<a href="tel:{{ preg_replace('/[^\d+]/', '', $v) }}">{{ $v }}</a>
                                            @else{{ $v }}@endif
                                        </dd>
                                    </div>
                                @endif
                            @endforeach
                        </dl>
                    @endif
                    <div class="detail-cta">
                        @if ($price && ($pv = S::format($record, $price)))
                            <div class="price-box"><small>{{ $price['label'] }}</small><span class="price price-lg">{{ $pv }}</span></div>
                        @endif
                        <a href="{{ route('contact', ['subject' => $title]) }}" class="btn btn-accent btn-lg">{{ $t['primary_cta_text'] }}</a>
                    </div>
                </div>
            </div>
        </div>
    </section>

    @if ($longs->filter(fn ($f) => $record->{$f['name']})->isNotEmpty())
        <section class="section">
            <div class="container narrow prose">
                @foreach ($longs as $f)
                    @if ($record->{$f['name']})
                        @if (! $loop->first || $longs->count() > 1)<h2>{{ $f['label'] }}</h2>@endif
                        {{ S::md($record->{$f['name']}) }}
                    @endif
                @endforeach
            </div>
        </section>
    @endif

    @if ($others->isNotEmpty())
        <section class="section section-alt">
            <div class="container">
                <div class="section-head">
                    <div><span class="eyebrow">Keşfetmeye devam edin</span><h2>Diğer {{ mb_strtolower($meta['label_plural']) }}</h2></div>
                    <a href="{{ url('/'.$meta['name']) }}" class="link-arrow">Tümünü gör <span aria-hidden="true">→</span></a>
                </div>
                @include('site.sections.cards', ['meta' => $meta, 'records' => $others])
            </div>
        </section>
    @endif
@endsection
