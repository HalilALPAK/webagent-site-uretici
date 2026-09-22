@extends('site.layout')
@php use App\Support\SiteConfig as S; @endphp
@section('title', 'Arama — '.S::get('site_name'))

@section('content')
    <section class="page-header">
        <div class="container narrow">
            <h1>Ne arıyorsunuz?</h1>
            <form method="get" class="search-inline search-lg" role="search">
                <label class="sr-only" for="q">Arama</label>
                <input id="q" type="search" name="q" value="{{ $q }}" placeholder="Anahtar kelime yazın…" autofocus>
                <button class="btn btn-primary">Ara</button>
            </form>
        </div>
    </section>
    <section class="section">
        <div class="container">
            @forelse ($results as $group)
                <div class="section-head"><h2>{{ $group['meta']['label_plural'] }}</h2></div>
                @include('site.sections.cards', ['meta' => $group['meta'], 'records' => $group['records']])
                <div class="spacer"></div>
            @empty
                @if ($q !== '')
                    <p class="empty">“{{ $q }}” için sonuç bulunamadı.</p>
                @endif
            @endforelse
        </div>
    </section>
@endsection
