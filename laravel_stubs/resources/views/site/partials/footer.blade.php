@php use App\Support\SiteConfig as S; @endphp
<footer class="site-footer">
    @if (S::get('newsletter'))
        <div class="container newsletter" id="newsletter">
            <div>
                <h2 class="newsletter-title">Haberdar olun</h2>
                <p>Kampanyalar ve yenilikler ayda en fazla iki e-postayla gelsin.</p>
            </div>
            <form method="post" action="{{ route('newsletter') }}" class="newsletter-form">
                @csrf
                <label class="sr-only" for="nl-email">E-posta adresiniz</label>
                <input id="nl-email" type="email" name="email" placeholder="E-posta adresiniz" required>
                <button class="btn btn-primary">Abone ol</button>
            </form>
            @if (session('subscribed'))
                <p class="newsletter-ok" role="status">Teşekkürler, aboneliğiniz alındı.</p>
            @endif
        </div>
    @endif

    <div class="container footer-grid">
        <div class="footer-brand">
            <a href="{{ url('/') }}" class="logo">
                @if (S::logo())<img src="{{ S::logo() }}" alt="{{ S::get('site_name') }}" class="logo-img">
                @else<span class="logo-mark" aria-hidden="true">{{ S::initial(S::get('site_name')) }}</span>@endif
                <span class="logo-text">{{ S::get('site_name') }}</span>
            </a>
            <p>{{ S::get('tagline') }}</p>
        </div>
        <div>
            <h3>Keşfet</h3>
            @foreach (S::entities() as $e)
                @if ($e['public'])
                    <a href="{{ url('/'.$e['name']) }}">{{ $e['label_plural'] }}</a>
                @endif
            @endforeach
        </div>
        <div>
            <h3>Kurumsal</h3>
            @foreach (S::get('pages', []) as $p)
                <a href="{{ route('page', $p['slug']) }}">{{ $p['title'] }}</a>
            @endforeach
            <a href="{{ route('contact') }}">İletişim</a>
        </div>
        <div>
            <h3>İletişim</h3>
            <a href="tel:{{ preg_replace('/[^\d+]/', '', S::get('contact_phone')) }}">{{ S::get('contact_phone') }}</a>
            <a href="mailto:{{ S::get('contact_email') }}">{{ S::get('contact_email') }}</a>
            <span>{{ S::get('address') }}</span>
        </div>
    </div>
    <div class="container footer-bottom">
        <span>© {{ date('Y') }} {{ S::get('site_name') }}</span>
        <span class="footer-links">
            @if (S::get('image_credits'))<a href="{{ route('credits') }}">Görsel kaynakları</a>@endif
            <a href="{{ url('/admin') }}">Yönetim</a>
        </span>
    </div>
</footer>
