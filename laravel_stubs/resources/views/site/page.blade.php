@extends('site.layout')
@php use App\Support\SiteConfig as S; @endphp
@section('title', $page['title'].' — '.S::get('site_name'))

@section('content')
    <section class="page-header">
        <div class="container narrow">
            <nav class="breadcrumb" aria-label="Konum"><a href="{{ url('/') }}">Ana sayfa</a> <span>/</span> {{ $page['title'] }}</nav>
            <h1>{{ $page['title'] }}</h1>
        </div>
    </section>
    <section class="section">
        <div class="container narrow prose">{{ S::md($page['body_markdown']) }}</div>
    </section>
@endsection
