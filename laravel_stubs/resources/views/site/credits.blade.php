@extends('site.layout')
@php use App\Support\SiteConfig as S; @endphp
@section('title', 'Görsel kaynakları — '.S::get('site_name'))

@section('content')
    <section class="page-header">
        <div class="container">
            <nav class="breadcrumb" aria-label="Konum"><a href="{{ url('/') }}">Ana sayfa</a> <span>/</span> Görsel kaynakları</nav>
            <h1>Görsel kaynakları</h1>
            <p class="section-sub">Bu sitedeki örnek fotoğraflar Creative Commons lisanslıdır ve Openverse aracılığıyla bulunmuştur.</p>
        </div>
    </section>
    <section class="section">
        <div class="container">
            @if (empty($credits))
                <p class="empty">Atıf gerektiren görsel yok.</p>
            @else
                <ul class="credits">
                    @foreach ($credits as $c)
                        <li>
                            <img src="{{ S::url($c['file']) }}" alt="" loading="lazy">
                            <span>
                                @if ($c['source_url'])<a href="{{ $c['source_url'] }}" target="_blank" rel="noopener nofollow">{{ $c['title'] ?: 'Adsız' }}</a>@else{{ $c['title'] }}@endif
                                <small>{{ $c['creator'] ?: 'Bilinmeyen' }} ·
                                    @if ($c['license_url'])<a href="{{ $c['license_url'] }}" target="_blank" rel="noopener nofollow">{{ $c['license'] }}</a>@else{{ $c['license'] }}@endif
                                </small>
                            </span>
                        </li>
                    @endforeach
                </ul>
            @endif
        </div>
    </section>
@endsection
