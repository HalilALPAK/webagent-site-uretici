<div class="grid grid-3">
    @foreach ($records as $r)
        @include('site.partials.card', ['r' => $r, 'meta' => $meta])
    @endforeach
</div>
