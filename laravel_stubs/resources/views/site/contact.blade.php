@extends('site.layout')
@php use App\Support\SiteConfig as S; @endphp
@section('title', 'İletişim — '.S::get('site_name'))

@section('content')
    <section class="page-header">
        <div class="container">
            <nav class="breadcrumb" aria-label="Konum"><a href="{{ url('/') }}">Ana sayfa</a> <span>/</span> İletişim</nav>
            <h1>Size nasıl yardımcı olabiliriz?</h1>
            <p class="section-sub">Formu doldurun, en kısa sürede dönüş yapalım.</p>
        </div>
    </section>

    <section class="section">
        <div class="container contact-grid">
            <form method="post" action="{{ route('contact.store') }}" class="form panel" novalidate>
                @csrf
                @if (session('sent'))
                    <div class="alert alert-ok" role="status">Mesajınız alındı, teşekkür ederiz!</div>
                @endif
                <input type="text" name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">

                <div class="field-row">
                    <div @class(['field', 'has-error' => $errors->has('name')])>
                        <label for="name">Ad soyad</label>
                        <input id="name" name="name" value="{{ old('name') }}" required autocomplete="name">
                        @error('name')<small class="error">{{ $message }}</small>@enderror
                    </div>
                    <div @class(['field', 'has-error' => $errors->has('email')])>
                        <label for="email">E-posta</label>
                        <input id="email" type="email" name="email" value="{{ old('email') }}" required autocomplete="email">
                        @error('email')<small class="error">{{ $message }}</small>@enderror
                    </div>
                </div>
                <div class="field-row">
                    <div class="field">
                        <label for="phone">Telefon <span class="optional">(isteğe bağlı)</span></label>
                        <input id="phone" name="phone" value="{{ old('phone') }}" autocomplete="tel">
                    </div>
                    <div class="field">
                        <label for="subject">Konu</label>
                        <input id="subject" name="subject" value="{{ old('subject', request('subject')) }}">
                    </div>
                </div>
                <div @class(['field', 'has-error' => $errors->has('body')])>
                    <label for="body">Mesajınız</label>
                    <textarea id="body" name="body" rows="6" required>{{ old('body') }}</textarea>
                    @error('body')<small class="error">{{ $message }}</small>@enderror
                </div>
                <button class="btn btn-accent btn-lg">Gönder</button>
            </form>

            <aside class="contact-card">
                <h2>{{ S::get('site_name') }}</h2>
                <ul class="contact-list">
                    <li>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/></svg>
                        <span><small>Telefon</small><a href="tel:{{ preg_replace('/[^\d+]/', '', S::get('contact_phone')) }}">{{ S::get('contact_phone') }}</a></span>
                    </li>
                    <li>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>
                        <span><small>E-posta</small><a href="mailto:{{ S::get('contact_email') }}">{{ S::get('contact_email') }}</a></span>
                    </li>
                    <li>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 22s7-6.1 7-12a7 7 0 1 0-14 0c0 5.9 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>
                        <span><small>Adres</small>{{ S::get('address') }}</span>
                    </li>
                </ul>
            </aside>
        </div>
    </section>
@endsection
