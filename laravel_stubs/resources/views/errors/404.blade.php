@extends('site.layout')
@section('title', 'Sayfa bulunamadı')

@section('content')
    <section class="section">
        <div class="container narrow center">
            <span class="eyebrow">404</span>
            <h1>Aradığınız sayfa bulunamadı</h1>
            <p class="lead">Bağlantı değişmiş ya da sayfa kaldırılmış olabilir.</p>
            <a href="{{ url('/') }}" class="btn btn-accent btn-lg">Ana sayfaya dön</a>
        </div>
    </section>
@endsection
