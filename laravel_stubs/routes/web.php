<?php

use App\Http\Controllers\SiteController;
use App\Support\SiteConfig;
use Illuminate\Support\Facades\Route;

// Yalnızca site.json'da public olan varlıklar URL alır.
$public = collect(SiteConfig::entities())->where('public', true)->pluck('name')->implode('|') ?: 'no-public-entities';

Route::get('/', [SiteController::class, 'home'])->name('home');
Route::get('/p/{slug}', [SiteController::class, 'page'])->name('page');
Route::get('/contact', [SiteController::class, 'contact'])->name('contact');
Route::post('/contact', [SiteController::class, 'contactStore'])->middleware('throttle:10,1')->name('contact.store');
Route::post('/newsletter', [SiteController::class, 'newsletter'])->middleware('throttle:10,1')->name('newsletter');
Route::get('/search', [SiteController::class, 'search'])->name('search');
Route::get('/credits', [SiteController::class, 'credits'])->name('credits');

Route::get('/api/{entity}', [SiteController::class, 'apiIndex'])->where('entity', $public)->name('api.index');
Route::get('/api/{entity}/{id}', [SiteController::class, 'apiShow'])->where('entity', $public)->whereNumber('id')->name('api.show');

Route::get('/{entity}', [SiteController::class, 'index'])->where('entity', $public)->name('entity.index');
Route::get('/{entity}/{id}', [SiteController::class, 'show'])->where('entity', $public)->whereNumber('id')->name('entity.show');
