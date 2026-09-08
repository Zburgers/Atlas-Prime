import { SearchClient } from "./search-client";

type SearchPageProps = {
  searchParams: Promise<{ q?: string }>;
};

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  return <SearchClient initialQuery={typeof params.q === "string" ? params.q : ""} />;
}
