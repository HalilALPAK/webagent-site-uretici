@php use App\Support\SiteConfig as S; $body = S::bodyField($meta); @endphp
<div class="faq">
    @foreach ($records as $r)
        <details @if ($loop->first) open @endif>
            <summary>{{ S::title($r, $meta) }}</summary>
            <div class="faq-answer prose">{{ S::md($body ? $r->{$body['name']} : '') }}</div>
        </details>
    @endforeach
</div>
