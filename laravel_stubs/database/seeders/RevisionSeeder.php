<?php

namespace Database\Seeders;

use App\Support\SiteConfig;
use Illuminate\Database\Seeder;

/**
 * Revizyonlarda yalnızca YENİ eklenen tabloların örnek içeriğini yükler (revision-seed.json).
 * Var olan kayıtlara dokunmaz; tablo zaten doluysa atlar.
 */
class RevisionSeeder extends Seeder
{
    public function run(): void
    {
        $path = base_path('revision-seed.json');
        $seed = is_file($path) ? json_decode(file_get_contents($path), true) : [];
        if (! $seed) {
            return;
        }

        $ids = [];
        $pending = [];
        foreach (SiteConfig::entities() as $entity) {
            $rows = $seed[$entity['name']] ?? [];
            $class = SiteConfig::modelClass($entity);
            if (! $rows || $class::query()->exists()) {
                continue;  // dolu tabloya yeniden içerik eklenmez
            }
            foreach ($rows as $row) {
                $data = [];
                $relations = [];
                foreach ($entity['fields'] as $field) {
                    if (! array_key_exists($field['name'], $row)) {
                        continue;
                    }
                    if ($field['type'] === 'relation') {
                        $relations[SiteConfig::column($field)] = [$field['relation'], (int) $row[$field['name']]];
                    } else {
                        $data[SiteConfig::column($field)] = $row[$field['name']];
                    }
                }
                $record = $class::create($data);
                $ids[$entity['name']][] = $record->getKey();
                if ($relations) {
                    $pending[] = [$record, $relations];
                }
            }
        }

        foreach ($pending as [$record, $relations]) {
            foreach ($relations as $column => [$target, $position]) {
                if ($id = $ids[$target][$position - 1] ?? null) {
                    $record->{$column} = $id;
                }
            }
            $record->save();
        }
    }
}
