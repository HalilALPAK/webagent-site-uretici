@extends('site.layout')
@php use App\Support\SiteConfig as S; $t = S::all()['theme']; @endphp

@section('content')
    @include('site.hero.'.$t['hero_variant'])

    @if (! empty($t['trust_items']))
        <section class="trust-strip" aria-label="Neden biz">
            <div class="container trust-inner">
                @foreach ($t['trust_items'] as $item)
                    <div class="trust-item reveal">
                        <span class="trust-dot" aria-hidden="true">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                        </span>
                        <span>{{ $item }}</span>
                    </div>
                @endforeach
            </div>
        </section>
    @endif

    @foreach ($sections as $s)
        <section @class(['section', 'section-alt' => $loop->even, 'section-dark' => $s['display'] === 'stats', 'section-split' => $s['display'] === 'faq'])>
            <div class="container">
                @include('site.partials.section-head', ['section' => $s, 'meta' => $s['meta']])
                @include('site.sections.'.$s['display'], ['meta' => $s['meta'], 'records' => $s['records']])
            </div>
        </section>
    @endforeach

    <section class="cta-band reveal">
        <div class="container cta-inner">
            <div>
                <h2>{{ $t['cta_band_title'] }}</h2>
                <p>{{ $t['cta_band_text'] }}</p>
            </div>
            <a href="{{ $t['primary_cta_link'] }}" class="btn btn-accent btn-lg">{{ $t['primary_cta_text'] }}</a>
        </div>
    </section>
@endsection
