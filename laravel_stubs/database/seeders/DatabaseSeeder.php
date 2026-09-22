<?php

namespace Database\Seeders;

use App\Models\User;
use App\Support\SiteConfig;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    /**
     * Yönetici hesabını ve seed.json'daki örnek içeriği yükler.
     * relation alanları seed.json'da "hedef varlıktaki N. kayıt" olarak gelir.
     */
    public function run(): void
    {
        User::updateOrCreate(
            ['email' => env('ADMIN_EMAIL', 'admin@example.com')],
            ['name' => 'Yönetici', 'password' => Hash::make(env('ADMIN_PASSWORD', 'password'))],
        );

        $path = base_path('seed.json');
        $seed = is_file($path) ? json_decode(file_get_contents($path), true) : [];
        $ids = [];
        $pending = [];

        foreach (SiteConfig::entities() as $entity) {
            $class = SiteConfig::modelClass($entity);
            foreach ($seed[$entity['name']] ?? [] as $row) {
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
                $record->{$column} = $ids[$target][$position - 1] ?? null;
            }
            $record->save();
        }
    }
}
