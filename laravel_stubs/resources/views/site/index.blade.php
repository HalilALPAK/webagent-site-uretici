@extends('site.layout')
@php use App\Support\SiteConfig as S; @endphp
@section('title', $meta['label_plural'].' — '.S::get('site_name'))

@section('content')
    <section class="page-header">
        <div class="container page-header-inner">
            <div>
                <nav class="breadcrumb" aria-label="Konum"><a href="{{ url('/') }}">Ana sayfa</a> <span>/</span> {{ $meta['label_plural'] }}</nav>
                <h1>{{ $meta['label_plural'] }}</h1>
                <p class="section-sub">{{ $records->total() }} kayıt</p>
            </div>
            <form method="get" class="search-inline" role="search">
                <label class="sr-only" for="q">{{ $meta['label_plural'] }} içinde ara</label>
                <input id="q" type="search" name="q" value="{{ $q }}" placeholder="{{ $meta['label_plural'] }} içinde ara…">
                <button class="btn btn-primary">Ara</button>
            </form>
        </div>
    </section>

    <section @class(['section', 'section-dark' => $display === 'stats'])>
        <div class="container">
            @if ($records->isEmpty())
                <p class="empty">Sonuç bulunamadı.</p>
            @else
                @include('site.sections.'.$display, ['meta' => $meta, 'records' => $records])
                {{ $records->links('site.partials.pagination') }}
            @endif
        </div>
    </section>
@endsection
