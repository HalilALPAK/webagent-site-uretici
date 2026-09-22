<?php

namespace App\Http\Controllers;

use App\Models\Message;
use App\Models\Subscriber;
use App\Support\SiteConfig;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class SiteController extends Controller
{
    /** Ana sayfa bölümlerinde gösterilecek kayıt sayısı (düzene göre). */
    private const HOME_LIMITS = ['feature' => 3, 'list' => 4, 'gallery' => 8, 'faq' => 6, 'team' => 4, 'stats' => 4];

    public function home(): View
    {
        $sections = [];
        foreach (SiteConfig::theme('home_sections', []) as $section) {
            $entity = SiteConfig::publicEntity($section['entity']);
            if (! $entity) {
                continue;
            }
            $records = SiteConfig::query($entity)->take(self::HOME_LIMITS[$section['display']] ?? 6)->get();
            if ($records->isNotEmpty()) {
                $sections[] = $section + ['meta' => $entity, 'records' => $records];
            }
        }

        return view('site.home', ['sections' => $sections]);
    }

    public function index(Request $request, string $entity): View
    {
        $meta = SiteConfig::publicEntity($entity) ?? abort(404);
        $query = SiteConfig::query($meta);

        if ($q = trim((string) $request->query('q'))) {
            $this->applySearch($query, $meta, $q);
        }

        return view('site.index', [
            'meta' => $meta,
            'records' => $query->paginate(12)->withQueryString(),
            'display' => SiteConfig::display($entity),
            'q' => $q,
        ]);
    }

    public function show(string $entity, int $id): View
    {
        $meta = SiteConfig::publicEntity($entity) ?? abort(404);
        $record = SiteConfig::query($meta)->findOrFail($id);
        $others = SiteConfig::query($meta)->whereKeyNot($id)->take(3)->get();

        return view('site.show', compact('meta', 'record', 'others'));
    }

    public function page(string $slug): View
    {
        $page = collect(SiteConfig::get('pages', []))->firstWhere('slug', $slug) ?? abort(404);

        return view('site.page', compact('page'));
    }

    public function contact(): View
    {
        return view('site.contact');
    }

    public function contactStore(Request $request): RedirectResponse
    {
        if ($request->filled('website')) { // bal küpü: botlar doldurur
            return redirect()->route('contact')->with('sent', true);
        }
        $data = $request->validate([
            'name' => ['required', 'string', 'max:120'],
            'email' => ['required', 'email', 'max:190'],
            'phone' => ['nullable', 'string', 'max:40'],
            'subject' => ['nullable', 'string', 'max:190'],
            'body' => ['required', 'string', 'min:5', 'max:5000'],
        ]);
        Message::create($data);

        return redirect()->route('contact')->with('sent', true);
    }

    public function newsletter(Request $request): RedirectResponse
    {
        $data = $request->validate(['email' => ['required', 'email', 'max:190']]);
        Subscriber::firstOrCreate($data);

        return redirect()->to(url('/').'#newsletter')->with('subscribed', true);
    }

    public function search(Request $request): View
    {
        $q = trim((string) $request->query('q'));
        $results = [];
        if ($q !== '') {
            foreach (SiteConfig::entities() as $meta) {
                if (! $meta['public']) {
                    continue;
                }
                $query = SiteConfig::query($meta);
                $this->applySearch($query, $meta, $q);
                if (($records = $query->take(6)->get())->isNotEmpty()) {
                    $results[] = ['meta' => $meta, 'records' => $records];
                }
            }
        }

        return view('site.search', compact('q', 'results'));
    }

    /** Openverse'ten gelen örnek görsellerin CC lisans atıfları. */
    public function credits(): View
    {
        return view('site.credits', ['credits' => SiteConfig::get('image_credits', [])]);
    }

    // ------------------------------------------------------------ JSON API (salt okunur)

    public function apiIndex(Request $request, string $entity): JsonResponse
    {
        $meta = SiteConfig::publicEntity($entity) ?? abort(404);
        $query = SiteConfig::query($meta);
        if ($q = trim((string) $request->query('q'))) {
            $this->applySearch($query, $meta, $q);
        }

        return response()->json($query->paginate(min(100, max(1, (int) $request->query('per_page', 20)))));
    }

    public function apiShow(string $entity, int $id): JsonResponse
    {
        $meta = SiteConfig::publicEntity($entity) ?? abort(404);

        return response()->json(SiteConfig::query($meta)->findOrFail($id));
    }

    private function applySearch($query, array $meta, string $q): void
    {
        $columns = collect($meta['fields'])
            ->whereIn('type', ['string', 'text', 'richtext', 'select', 'email'])
            ->map(fn ($f) => SiteConfig::column($f))->all();
        $query->where(function ($w) use ($columns, $q) {
            foreach ($columns as $col) {
                $w->orWhere($col, 'like', '%'.$q.'%');
            }
        });
    }
}
